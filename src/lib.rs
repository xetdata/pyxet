use gitxet::command::CliOverrides;
use gitxet::config_cmd::{load_config_with_args, load_config_with_path};
use gitxet::git_integration::git_repo::GitRepo;
use gitxet::git_integration::git_wrap::run_git_captured;
use gitxet::log::initialize_tracing_subscriber;
use gitxet::xetmnt::xetfs_bare::XetFSBare;
use nfsserve::nfs::*;
use nfsserve::vfs::*;
use pyo3::exceptions::*;
use pyo3::prelude::*;
use pyo3::types::{PyByteArray, PyBytes, PyList};
use pyo3_asyncio;
use std::collections::HashMap;
#[cfg(unix)]
use std::os::unix::ffi::OsStrExt;
#[cfg(windows)]
use std::os::windows::ffi::OsStrExt;
use std::path::{Component, Path, PathBuf};
use std::sync::Arc;
use tempfile::TempDir;
use tracing::error;
#[pyfunction]
pub fn clone(remote: String, no_smudge: bool) -> PyResult<()> {
    GitRepo::clone(&[&remote], no_smudge)
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to clone {:?}", e)))?;
    Ok(())
}

#[pyclass]
struct PyRepo {
    clone_path: PathBuf,
    cfg: gitxet::config_cmd::XetConfig,
    fs: HashMap<String, Arc<dyn NFSFileSystem + Send>>,
}

#[cfg(unix)]
fn os_str_to_bytes(s: &std::ffi::OsStr) -> Vec<u8> {
    s.as_bytes().to_owned()
}
#[cfg(windows)]
fn os_str_to_bytes(s: &OsStr) -> Vec<u8> {
    let u16string = &s.encode_wide().collect();
    let ustr = std::string::String::from_utf16_lossy(&u16string);
    ustr.as_bytes().to_vec()
}
#[cfg(windows)]
fn bytes_to_os_str(s: &[u8]) -> std::ffi::OsString {
    let ustr = std::string::String::from_utf8_lossy(&s);
    let u16str = ustr.encode_utf16.to_vec();
    OsString::from_wide(&u16str[..])
}
#[pyclass]
struct FileAttributes {
    #[pyo3(get)]
    pub ftype: String, // "directory"/"file"/"symlink"
    #[pyo3(get)]
    pub size: usize,
}

impl From<fattr3> for FileAttributes {
    fn from(attr: fattr3) -> Self {
        // convert to a string representation to return
        let ftype = match attr.ftype {
            ftype3::NF3REG => "file",
            ftype3::NF3DIR => "directory",
            ftype3::NF3LNK => "symlink",
            _ => "other",
        }
        .to_owned();

        FileAttributes {
            ftype,
            size: attr.size as usize,
        }
    }
}

impl PyRepo {
    fn path_to_fid(&mut self, branch: &str, path: &Path) -> PyResult<Option<fileid3>> {
        self.init_for_branch(branch.to_owned())?;
        let fs = self.fs.get(branch).unwrap().clone();
        let root = fs.root_dir();
        let mut v: Vec<fileid3> = Vec::new();
        v.push(root);
        for p in path.components() {
            match p {
                Component::CurDir => {}
                Component::RootDir => {}
                Component::Prefix(_) => {}
                Component::Normal(x) => {
                    let mut maybe_lookup = None;
                    let fname = nfsstring::from(os_str_to_bytes(x));
                    pyo3_asyncio::tokio::get_runtime().block_on(async {
                        maybe_lookup = Some(fs.lookup(v.last().unwrap().to_owned(), &fname).await);
                    });
                    match maybe_lookup {
                        Some(Err(_)) => return Ok(None),
                        Some(Ok(fid)) => {
                            v.push(fid);
                        }
                        None => {
                            return Err(PyRuntimeError::new_err(format!(
                                "Failed to block on tokio runtime"
                            )));
                        }
                    }
                }
                Component::ParentDir => {
                    if v.len() > 1 {
                        v.pop();
                    }
                }
            }
        }
        let final_fid = v.last().unwrap().to_owned();
        Ok(Some(final_fid))
    }
}
impl PyRepo {
    pub fn stat_fattr(&mut self, branch: String, path: PathBuf) -> PyResult<fattr3> {
        let maybe_fid = self.path_to_fid(&branch, &path)?;
        if let Some(fid) = maybe_fid {
            let fs = self.fs.get(&branch).unwrap().clone();
            let mut attr = None;
            pyo3_asyncio::tokio::get_runtime()
                .block_on(async { attr = Some(fs.getattr(fid).await) });
            // attr is a Option<Result<fattr3, nfsstat3>>
            let attr = attr
                .ok_or(PyRuntimeError::new_err("Failed to block on tokio runtime"))?
                .map_err(|e| PyIOError::new_err(format!("Failed to stat file {:?}", e)))?;

            Ok(attr)
        } else {
            Err(PyIOError::new_err("No such file or directory"))
        }
    }
}

#[pymethods]
impl PyRepo {
    #[new]
    pub fn new(url: String) -> PyResult<Self> {
        // clone the path
        let clone_dir = TempDir::new().unwrap();
        let mut clone_path = clone_dir.into_path();
        eprintln!("Setting up {:?}", url);
        run_git_captured(
            Some(&clone_path),
            "clone",
            &["--mirror", &url, "repo"],
            true,
            None,
        )
        .map_err(|e| {
            error!("{:?}", e);
            PyIOError::new_err(format!("Unable to clone repository. Err: {:?}", e))
        })?;
        clone_path.push("repo");

        let cfg = load_config_with_path(&clone_path).unwrap();
        let gitrepo = GitRepo::open(cfg.clone()).map_err(|e| {
            PyIOError::new_err({
                error!("{:?}", e);
                format!("Unable to open repository. Err: {:?}", e)
            })
        })?;
        pyo3_asyncio::tokio::get_runtime().block_on(async {
            let _ = gitrepo.sync_notes_to_dbs().await;
        });

        let mut res = PyRepo {
            clone_path,
            cfg,
            fs: HashMap::new(),
        };

        res.init_for_branch("main".to_owned()).map_err(|e| {
            error!("{:?}", e);
            e
        })?;
        Ok(res)
    }

    pub fn init_for_branch(&mut self, branch: String) -> PyResult<()> {
        if self.fs.contains_key(&branch) {
            return Ok(());
        }
        eprintln!("Initializing branch {:?}", branch);
        // create the main branch
        let mut maybe_xfs = None;
        pyo3_asyncio::tokio::get_runtime().block_on(async {
            maybe_xfs = Some(XetFSBare::new(&self.clone_path, &self.cfg, "main", 1).await);
        });
        if let Some(xfs) = maybe_xfs {
            let xfs = xfs.map_err(|e| {
                error!("{:?}", e);
                PyRuntimeError::new_err(format!("Unexpected error {:?}", e))
            })?;
            self.fs.insert(branch, Arc::new(xfs));
            Ok(())
        } else {
            Err(PyRuntimeError::new_err(format!(
                "Failed to block on tokio runtime"
            )))
        }
    }

    pub fn open(&mut self, branch: String, path: PathBuf) -> PyResult<PyROFileIO> {
        let maybe_fid = self.path_to_fid(&branch, &path)?;
        if let Some(fid) = maybe_fid {
            let fs = self.fs.get(&branch).unwrap().clone();
            Ok(PyROFileIO::new(fs.clone(), fid)?)
        } else {
            Err(PyIOError::new_err("No such file or directory"))
        }
    }

    pub fn stat(&mut self, branch: String, path: PathBuf) -> PyResult<FileAttributes> {
        self.stat_fattr(branch, path).map(|x| x.into())
    }

    pub fn readdir(
        &mut self,
        branch: String,
        path: PathBuf,
    ) -> PyResult<(Vec<String>, Vec<FileAttributes>)> {
        let maybe_fid = self.path_to_fid(&branch, &path)?;
        if let Some(fid) = maybe_fid {
            let fs = self.fs.get(&branch).unwrap().clone();
            let mut listing = None;
            pyo3_asyncio::tokio::get_runtime()
                .block_on(async { listing = Some(fs.readdir(fid, 0, usize::MAX).await) });
            let listing = listing
                .ok_or(PyRuntimeError::new_err("Failed to block on tokio runtime"))?
                .map_err(|e| PyIOError::new_err(format!("Failed to list {:?}", e)))?;
            let mut filenames: Vec<String> = Vec::new();
            let mut attributes: Vec<FileAttributes> = Vec::new();
            for ent in listing.entries.into_iter() {
                let ustr = std::string::String::from_utf8_lossy(&ent.name).to_string();
                filenames.push(ustr);
                attributes.push(ent.attr.into())
            }
            Ok((filenames, attributes))
        } else {
            Err(PyIOError::new_err("No such file or directory"))
        }
    }
}

#[pyclass(subclass)]
struct PyROFileIO {
    fs: Arc<dyn NFSFileSystem + Send>,
    id: fileid3,
    pos: u64,
    file_len: u64,
    #[pyo3(get)]
    pub closed: bool,
}

const MAX_READ_SIZE: u64 = 4 * 1024 * 1024; // 1MB
impl PyROFileIO {
    pub fn new(fs: Arc<dyn NFSFileSystem + Send>, fid: fileid3) -> PyResult<PyROFileIO> {
        let mut maybe_getattr = None;
        pyo3_asyncio::tokio::get_runtime().block_on(async {
            maybe_getattr = Some(fs.getattr(fid).await);
        });
        let file_len: u64;
        match maybe_getattr {
            Some(Err(_e)) => {
                return Err(PyIOError::new_err(format!("Unable to find path")));
            }
            Some(Ok(stat)) => {
                file_len = stat.size;
            }
            None => {
                return Err(PyRuntimeError::new_err(format!(
                    "Failed to block on tokio runtime"
                )));
            }
        }
        Ok(PyROFileIO {
            fs,
            id: fid,
            pos: 0,
            file_len,
            closed: false,
        })
    }

    pub fn readline_impl(&mut self, size: i64) -> PyResult<Vec<u8>> {
        let mut ret = Vec::new();
        let mut done: bool = false;
        while !done {
            let read_size = if size < 0 {
                // if size is unlimited, we read in 4K blocks
                MAX_READ_SIZE as i64
            } else {
                // otherwise 4K or size - amount_read_so_far
                std::cmp::min(size - (ret.len() as i64), MAX_READ_SIZE as i64)
            };
            // if we run out of read we are done
            if read_size <= 0 {
                break;
            }

            // actually do the read
            let mut fs_read = None;
            pyo3_asyncio::tokio::get_runtime().block_on(async {
                fs_read = Some(self.fs.read(self.id, self.pos, read_size as u32).await);
            });
            match fs_read {
                Some(Err(stat)) => {
                    return Err(PyIOError::new_err(format!(
                        "Unable to read from file: {:?}",
                        stat
                    )));
                }
                None => {
                    return Err(PyRuntimeError::new_err(format!(
                        "Failed to block on tokio runtime"
                    )));
                }
                Some(Ok((mut buf, eof))) => {
                    // if we find the '\n' we append that to the return buffer and flag done
                    if let Some(pos) = buf.iter().position(|&x| x == b'\n') {
                        ret.extend_from_slice(&buf[..pos + 1]);
                        // shift the read position to after the \n
                        self.pos += (pos + 1) as u64;
                        done = true;
                    } else {
                        // if we do not find the '\n' we just append to the return buffer
                        // shift the read position to after the buffer
                        // done only if we EOF
                        self.pos += buf.len() as u64;
                        ret.append(&mut buf);
                        done = eof;
                    }
                }
            }
        }

        Ok(ret)
    }

    pub fn read_impl(&mut self, size: u32) -> PyResult<Vec<u8>> {
        let mut fs_read = None;
        pyo3_asyncio::tokio::get_runtime().block_on(async {
            fs_read = Some(self.fs.read(self.id, self.pos, size).await);
        });
        match fs_read {
            Some(Err(stat)) => {
                eprintln!("FS read err {:?}", stat);
                return Err(PyIOError::new_err(format!(
                    "Unable to read from file: {:?}",
                    stat
                )));
            }
            None => {
                return Err(PyRuntimeError::new_err(format!(
                    "Failed to block on tokio runtime"
                )));
            }
            Some(Ok((buf, _))) => {
                self.pos += buf.len() as u64;
                return Ok(buf);
            }
        }
    }
}

#[pymethods]
impl PyROFileIO {
    pub fn close(&mut self) -> PyResult<()> {
        self.closed = true;
        Ok(())
    }
    pub fn readable(&self) -> PyResult<bool> {
        Ok(!self.closed)
    }
    pub fn seekable(&self) -> PyResult<bool> {
        Ok(true)
    }
    pub fn writable(&self) -> PyResult<bool> {
        Ok(false)
    }
    pub fn tell(&self) -> PyResult<u64> {
        Ok(self.pos)
    }
    #[pyo3(signature = (offset, whence=0))]
    pub fn seek(&mut self, offset: i64, whence: usize) -> PyResult<u64> {
        const SEEK_SET: usize = 0;
        const SEEK_CUR: usize = 1;
        const SEEK_END: usize = 2;
        match whence {
            SEEK_SET => {
                self.pos = offset as u64;
            }
            SEEK_CUR => {
                self.pos = (self.pos as i64 + offset) as u64;
            }
            SEEK_END => {
                self.pos = ((self.file_len as i64) + offset) as u64;
            }
            _ => {
                return Err(PyValueError::new_err("Invalid Seek Whence"));
            }
        }
        if self.pos >= self.file_len {
            self.pos = self.file_len;
        }
        Ok(self.pos)
    }
    // why does IOBase have readline? this is not very nice.
    #[pyo3(signature = (size=-1))]
    pub fn readline(&mut self, size: i64, py: Python<'_>) -> PyResult<PyObject> {
        let ret = self.readline_impl(size)?;
        Ok(PyBytes::new(py, &ret).into())
    }
    #[pyo3(signature = (num_lines=-1))]
    pub fn readlines(&mut self, num_lines: i64, py: Python<'_>) -> PyResult<PyObject> {
        let ret = PyList::empty(py);
        while num_lines <= 0 || (ret.len() as i64) < num_lines {
            let buf = self.readline_impl(-1)?;
            if buf.len() > 0 {
                let _ = ret.append(PyBytes::new(py, &buf));
            } else {
                break;
            }
        }
        Ok(ret.into())
    }

    #[pyo3(signature = (size=-1))]
    pub fn read(&mut self, size: i64, py: Python<'_>) -> PyResult<PyObject> {
        // if size is <=0, its basically readall
        if size <= 0 {
            return self.readall(py);
        }
        let size = std::cmp::min(size as u64, u32::MAX as u64);
        let ret = self.read_impl(size as u32)?;
        Ok(PyBytes::new(py, &ret).into())
    }
    pub fn readall(&mut self, py: Python<'_>) -> PyResult<PyObject> {
        let mut ret = Vec::new();
        while self.pos < self.file_len {
            ret.extend(self.read_impl(MAX_READ_SIZE as u32)?);
        }
        Ok(PyBytes::new(py, &ret).into())
    }
    pub fn readinto1(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<u64> {
        let buf = PyByteArray::from(py, b)?;
        let buflen = buf.len();

        let read_size = std::cmp::min(buflen as u64, MAX_READ_SIZE);
        let readres = self.read_impl(read_size as u32)?;
        let readlen = readres.len();

        if readlen > 0 {
            let bufbytes = unsafe { buf.as_bytes_mut() };
            bufbytes[..readlen].copy_from_slice(&readres);
        }
        Ok(readlen as u64)
    }

    pub fn readinto(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<u64> {
        let buf = PyByteArray::from(py, b)?;
        let buflen = buf.len();
        let bufbytes = unsafe { buf.as_bytes_mut() };

        let mut curoff: usize = 0;
        while self.pos < self.file_len {
            let read_size = std::cmp::min(buflen - curoff, MAX_READ_SIZE as usize);
            let readres = self.read_impl(read_size as u32)?;
            let readlen = readres.len();

            bufbytes[curoff..curoff + readlen].copy_from_slice(&readres);
            curoff += readlen;
        }
        Ok(curoff as u64)
    }
}

/// This module is implemented in Rust.
#[pymodule]
pub fn rpyxet(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    let cli_overrides = CliOverrides::default();
    let cfg = load_config_with_args(cli_overrides).unwrap();
    let _ = initialize_tracing_subscriber(&cfg);
    m.add_function(wrap_pyfunction!(clone, m)?)?;
    m.add_class::<PyRepo>()?;

    Ok(())
}
