use anyhow::anyhow;
use gitxetcore::command::login::*;
use gitxetcore::command::mount::*;
use gitxetcore::command::*;
use gitxetcore::config::ConfigGitPathOption;
use gitxetcore::config::ConfigGitPathOption::NoPath;
use gitxetcore::config::XetConfig;
use gitxetcore::git_integration::git_repo::is_user_identity_set;
use gitxetcore::log::initialize_tracing_subscriber;
use pyo3::exceptions::*;
use pyo3::prelude::*;
use pyo3::types::{PyByteArray, PyBytes, PyList};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use xetblob::*;

#[pyclass]
pub struct FileAttributes {
    #[pyo3(get)]
    pub ftype: String, // "directory"/"file"/"symlink"
    #[pyo3(get)]
    pub size: usize,
}

impl From<DirEntry> for FileAttributes {
    fn from(ent: DirEntry) -> Self {
        let ftype = match ent.object_type.as_str() {
            "dir" => "directory",
            "blob" => "file",
            "blob+exec" => "file",
            "link" => "symlink",
            "branch" => "branch",
            "repo" => "repo",
            _ => "file",
        };
        FileAttributes {
            ftype: ftype.to_string(),
            size: ent.size as usize,
        }
    }
}

fn anyhow_to_runtime_error(e: anyhow::Error) -> PyErr {
    PyRuntimeError::new_err(format!("{e:?}"))
}

macro_rules! rust_async {
    ($py:ident, $xp:expr) => {{
        let mut res = Option::<Result<_, _>>::None;
        let mut err_res = Option::<anyhow::Error>::None;
        $py.allow_threads(|| {
            if let Err(e) = pyo3_asyncio::tokio::get_runtime().block_on(async {
                let r: Result<_, _> = { $xp };
                res = Some(r.map_err(|e| PyRuntimeError::new_err(format!("{e:?}"))));

                anyhow::Ok(())
            }) {
                err_res = Some(e);
            }
        });

        let ret: PyResult<_> = {
            if let Some(e) = err_res {
                Err(anyhow_to_runtime_error(e))
            } else {
                res.unwrap_or(Err(PyRuntimeError::new_err(
                    "Failed to block on tokio runtime",
                )))
            }
        };

        ret
    }};
}

#[pyclass]
struct PyRepoManager {
    manager: XetRepoManager,
}

#[pyfunction]
pub fn configure_login(
    host: String,
    user: String,
    email: String,
    token: String,
    no_auth: bool,
    no_overwrite: bool,
    py: Python<'_>,
) -> PyResult<()> {
    rust_async!(py, {
        let command = Command::Login(LoginArgs {
            host,
            user,
            email,
            password: token,
            force: no_auth,
            no_overwrite,
        });

        let config = XetConfig::new(None, None, ConfigGitPathOption::NoPath)?;
        command.run(config).await
    })
}

#[pyfunction]
pub fn perform_mount(
    python_exe: String,
    remote: String,
    path: String,
    reference: String,
    prefetch: Option<usize>,
    py: Python<'_>,
) -> PyResult<()> {
    let prefetch = prefetch.unwrap_or(2);
    #[cfg(target_os = "windows")]
    let command = {
        if path.len() > 1 {
            return Err(PyValueError::new_err("Target path must be a drive letter"));
        }
        Command::Mount(MountArgs {
            remote,
            drive: path,
            reference,
            foreground: false,
            prefetch,
            ip: "auto".to_string(),
            clonepath: None,
            writable: false,
            invoked_from_python: Some(python_exe),
            watch: None,
        })
    };

    #[cfg(not(target_os = "windows"))]
    let command = Command::Mount(MountArgs {
        remote,
        path: Some(std::path::PathBuf::from(&path)),
        reference,
        foreground: false,
        prefetch,
        ip: "127.0.0.1".to_string(),
        clonepath: None,
        writable: false,
        invoked_from_python: Some(python_exe),
        watch: None,
    });
    let config = XetConfig::new(None, None, ConfigGitPathOption::NoPath)
        .map_err(|x| anyhow!("Unable to obtain default config {x}"))
        .map_err(anyhow_to_runtime_error)?;

    rust_async!(py, command.run(config).await)
}

#[pyfunction]
pub fn perform_mount_curdir(
    path: std::path::PathBuf,
    reference: String,
    signal: i32,
    autostop: bool,
    prefetch: usize,
    ip: String,
    writable: bool,
    py: Python<'_>,
) -> PyResult<()> {
    let signal = if signal < 0 { None } else { Some(signal) };
    let command = Command::MountCurdir(MountCurdirArgs {
        path,
        reference,
        signal,
        autostop,
        prefetch,
        ip,
        writable,
        watch: None,
    });

    let config = XetConfig::new(None, None, ConfigGitPathOption::CurdirDiscover)
        .map_err(|x| anyhow!("Unable to obtain default config {x}"))
        .map_err(anyhow_to_runtime_error)?;

    rust_async!(py, command.run(config).await)
}

#[pymethods]
impl PyRepoManager {
    #[new]
    pub fn new() -> PyResult<Self> {
        let manager = XetRepoManager::new(None, None).map_err(anyhow_to_runtime_error)?;
        if !is_user_identity_set(None).unwrap_or(false) {
            eprintln!(
                "Please configure your Git user name and email. \
\n\n  git config --global user.name \"<Name>\"\n  git config --global user.email \"<Email>\""
            );
        }
        Ok(PyRepoManager { manager })
    }

    // return the current user name
    pub fn get_inferred_username(&self, remote: &str) -> PyResult<String> {
        self.manager
            .get_inferred_username(remote)
            .map_err(anyhow_to_runtime_error)
    }

    /// Performs a file listing.
    pub fn listdir(
        &self,
        remote: &str,
        branch: &str,
        path: &str,
        py: Python<'_>,
    ) -> PyResult<(Vec<String>, Vec<FileAttributes>)> {
        // strip trailing slashes
        #![allow(clippy::manual_strip)]
        let path = if path.ends_with('/') {
            &path[..path.len() - 1]
        } else {
            path
        };
        let path = if path.starts_with('/') {
            &path[1..]
        } else {
            path
        };
        let listing = rust_async!(py, self.manager.listdir(remote, branch, path).await)?;
        let mut ret_names = vec![];
        let mut ret_attrs = vec![];
        for i in listing {
            if path.is_empty() {
                ret_names.push(i.name.clone());
            } else {
                ret_names.push(format!("{path}/{}", i.name).to_string());
            }
            ret_attrs.push(i.into());
        }

        Ok((ret_names, ret_attrs))
    }

    /// Performs a general api query.
    pub fn api_query(
        &self,
        remote: &str,
        op: &str,
        http_command: &str,
        body: &str,
        py: Python<'_>,
    ) -> PyResult<Vec<u8>> {
        rust_async!(
            py,
            self.manager
                .perform_api_query(remote, op, http_command, body)
                .await
        )
    }

    /// Gets status of a path
    pub fn override_login_config(
        &mut self,
        user_name: &str,
        user_token: &str,
        email: Option<&str>,
        host: Option<&str>,
        py: Python<'_>,
    ) -> PyResult<()> {
        rust_async!(
            py,
            self.manager
                .override_login_config(user_name, user_token, email, host)
                .await
        )
    }

    /// Gets status of a path
    pub fn stat(
        &self,
        remote: &str,
        branch: &str,
        path: &str,
        py: Python<'_>,
    ) -> PyResult<Option<FileAttributes>> {
        let ent: Option<DirEntry> = rust_async!(py, self.manager.stat(remote, branch, path).await)?;

        Ok(ent.map(|x| x.into()))
    }

    /// Obtains access to a repo
    pub fn get_repo(&mut self, remote: &str, py: Python<'_>) -> PyResult<PyRepo> {
        rust_async!(py, {
            let repo = self.manager.get_repo(None, remote).await?;
            anyhow::Ok(PyRepo { repo })
        })
    }
}
#[pyclass]
struct PyRepo {
    repo: Arc<XetRepo>,
}
#[pymethods]
impl PyRepo {
    pub fn open_for_read(&self, branch: &str, path: &str, py: Python<'_>) -> PyResult<PyRFile> {
        rust_async!(
            py,
            PyRFile::new(self.repo.open_for_read(branch, path).await?))
        
    }
    pub fn begin_write_transaction(
        &self,
        branch: &str,
        commit_message: &str,
        py: Python<'_>,
    ) -> PyResult<PyWriteTransaction> {
        rust_async!(py, {
         let transaction: XetRepoWriteTransaction =
             self.repo.begin_write_transaction(branch, None, None).await?;
        anyhow::Ok(PyWriteTransaction {
             transaction: Some(transaction),
             message: commit_message.to_owned(),
             ..Default::default()
         })})
    }

    /// Fetch shards that could be useful for dedup, according to the given endpoints.
    ///
    /// Endpoints are given as a list of (branch, path) tuples.  Shard hint fetches may be
    /// across branches.
    ///
    /// If min_num_bytes_in_dedup is specified, then only shards that collectively define
    /// that many bytes are actually downloaded; any hinted shards that don't specify at least
    /// the minimum number of bytes in chunks are ignored.
    ///
    pub fn fetch_hinted_shards_for_dedup(
        &self,
        file_paths: Vec<(&str, &str)>,
        min_dedup_bytes_for_shard_downloading: Option<usize>,
        py: Python<'_>,
    ) -> PyResult<()> {
       rust_async!(py,
            self.repo
                .fetch_hinted_shards_for_dedup(
                    &file_paths,
                    min_dedup_bytes_for_shard_downloading.unwrap_or(0)
                )
                .await
        )
    }
}

#[pyclass(subclass)]
struct PyRFile {
    reader: XetRFileObject,
    pos: u64,
    file_len: u64,
    #[pyo3(get)]
    pub closed: bool,
}

const MAX_READ_SIZE: u64 = 8 * 1024 * 1024; // 8MB
impl PyRFile {
    fn new(reader: XetRFileObject) -> PyResult<PyRFile> {
        let len = reader.len();
        Ok(PyRFile {
            reader,
            pos: 0,
            file_len: len as u64,
            closed: false,
        })
    }

    pub async fn readline_impl(&mut self, size: i64) -> anyhow::Result<Vec<u8>> {
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
            let fs_read = self.reader.read(self.pos, read_size as u32).await?;
            let (mut buf, eof) = fs_read;
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

        Ok(ret)
    }

    pub async fn read_impl(&mut self, size: u32) -> anyhow::Result<Vec<u8>> {
        let fs_read = self.reader.read(self.pos, size).await?;

        let (buf, _) = fs_read;
        self.pos += buf.len() as u64;
        Ok(buf)
    }
}

#[pymethods]
impl PyRFile {
    pub fn is_closed(&mut self) -> PyResult<bool> {
        Ok(self.closed)
    }
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
        let ret = rust_async!(py, self.readline_impl(size).await)?;
        Ok(PyBytes::new(py, &ret).into())
    }

    #[pyo3(signature = (num_lines=-1))]
    pub fn readlines(&mut self, num_lines: i64, py: Python<'_>) -> PyResult<PyObject> {
        let v_buf = rust_async!(py, {
            let mut v_buf = Vec::new();

            while num_lines <= 0 || (v_buf.len() as i64) < num_lines {
                let buf = self.readline_impl(-1).await?; // TODO: This has to be wrong re num_lines, given the API??
                if !buf.is_empty() {
                    v_buf.push(buf);
                } else {
                    break;
                }
            }
            anyhow::Ok(v_buf)
        })?;

        let ret = PyList::empty(py);

        for buf in v_buf {
            ret.append(PyBytes::new(py, &buf))?;
        }
        Ok(ret.into())
    }

    #[pyo3(signature = (size=-1))]
    pub fn read(&mut self, size: i64, py: Python<'_>) -> PyResult<PyObject> {
        // if size is <=0, its basically readall
        if size <= 0 {
            return self.readall(py);
        }
        let ret = rust_async!(py, {
            let size = std::cmp::min(size as u64, u32::MAX as u64);
            self.read_impl(size as u32).await
        })?;
        Ok(PyBytes::new(py, &ret).into())
    }

    pub fn readall(&mut self, py: Python<'_>) -> PyResult<PyObject> {
        let ret = rust_async!(py, {
            let mut ret = Vec::new();
            while self.pos < self.file_len {
                ret.extend(self.read_impl(MAX_READ_SIZE as u32).await?);
            }
            anyhow::Ok(ret)
        })?;
        Ok(PyBytes::new(py, &ret).into())
    }
    pub fn readinto1(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<u64> {
        let buf = PyByteArray::from(py, b)?;
        let buflen = buf.len();
        let bufbytes = unsafe { buf.as_bytes_mut() };

        rust_async!(py, {
            let read_size = std::cmp::min(buflen as u64, MAX_READ_SIZE);
            let readres = self.read_impl(read_size as u32).await?;
            let readlen = readres.len();

            if readlen > 0 {
                bufbytes[..readlen].copy_from_slice(&readres);
            }
            anyhow::Ok(readlen as u64)
        })
    }

    pub fn readinto(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<u64> {
        let buf = PyByteArray::from(py, b)?;
        let buflen = buf.len();
        let bufbytes = unsafe { buf.as_bytes_mut() };

        rust_async!(py, {
            let mut curoff: usize = 0;
            while self.pos < self.file_len {
                let read_size = std::cmp::min(buflen - curoff, MAX_READ_SIZE as usize);
                let readres = self.read_impl(read_size as u32).await?;
                let readlen = readres.len();

                bufbytes[curoff..curoff + readlen].copy_from_slice(&readres);
                curoff += readlen;
            }
            anyhow::Ok(curoff as u64)
        })
    }

    pub fn write(&mut self, _b: &PyAny, _py: Python<'_>) -> PyResult<()> {
        Err(PyRuntimeError::new_err("Readonly file"))
    }
}

#[pyclass(subclass)]
#[derive(Default)]
struct PyWriteTransaction {
    transaction: Option<XetRepoWriteTransaction>,
    branch: String,
    #[pyo3(get)]
    new_files: Vec<String>,
    #[pyo3(get)]
    copies: Vec<(String, String)>,
    #[pyo3(get)]
    deletes: Vec<String>,
    #[pyo3(get)]
    moves: Vec<(String, String)>,
    do_not_commit: bool,
    error_on_commit: bool,
    ready_to_commit: bool,
    pending_write_files: AtomicU32,
    message: String,
}

#[pymethods]
impl PyWriteTransaction {
    /// This is for testing
    pub fn set_do_not_commit(&mut self, do_not_commit: bool) -> PyResult<()> {
        self.do_not_commit = do_not_commit;
        Ok(())
    }
    /// This is for testing
    pub fn set_error_on_commit(&mut self, error_on_commit: bool) -> PyResult<()> {
        self.error_on_commit = error_on_commit;
        Ok(())
    }
    pub fn open_for_write(&mut self, path: &str, py: Python<'_>) -> PyResult<PyWFile> {
        if let Some(ref mut tr) = self.transaction {
            self.new_files
                .push(format!("{}/{path}", self.branch).to_string());
            let writer = rust_async!(py, tr.open_for_write(path).await)?;
            self.pending_write_files.fetch_add(1, Ordering::SeqCst);

            Ok(PyWFile { writer })
        } else {
            Err(PyRuntimeError::new_err("Transaction already committed"))
        }
    }
    pub fn set_ready(&mut self, py: Python<'_>) -> PyResult<()> {
        let val = self.pending_write_files.load(Ordering::SeqCst);

        // We need to check here because if all write files finished before this
        // then none of them sees the ready signal.
        if val == 0 {
            // All write files finished
            self.commit(py)
        } else {
            // Some files are pending, signal them to commit when they finish
            self.ready_to_commit = true;
            Ok(())
        }
    }
    pub fn finish_write_one(&mut self, py: Python<'_>) -> PyResult<()> {
        let val = self.pending_write_files.fetch_sub(1, Ordering::SeqCst);
        // The last write just finished
        if val == 1 && self.ready_to_commit {
            self.commit(py)
        } else {
            Ok(())
        }
    }
    pub fn transaction_size(&self, py: Python<'_>) -> PyResult<usize> {
        if let Some(ref tr) = self.transaction {
            rust_async!(py, anyhow::Ok(tr.transaction_size().await))
        } else {
            Ok(0)
        }
    }
    pub fn commit(&mut self, py: Python<'_>) -> PyResult<()> {
        if self.error_on_commit {
            return Err(PyRuntimeError::new_err("Error on commit flagged"));
        }
        if self.do_not_commit {
            return self.cancel(py);
        }
        let mut transaction = None;
        std::mem::swap(&mut self.transaction, &mut transaction);
        if transaction.is_none() {
            return Err(PyRuntimeError::new_err("Transaction already committed"));
        }
        let transaction = transaction.unwrap();
        rust_async!(py, transaction.commit(&self.message).await)
    }
    pub fn cancel(&mut self, py: Python<'_>) -> PyResult<()> {
        let mut transaction = None;
        std::mem::swap(&mut self.transaction, &mut transaction);
        if transaction.is_none() {
            return Err(PyRuntimeError::new_err("Transaction already committed"));
        }
        let transaction = transaction.unwrap();
        let _ = rust_async!(py, transaction.cancel().await);
        Ok(())
    }
    pub fn delete(&mut self, path: &str, py : Python<'_>) -> PyResult<()> {
        if let Some(ref mut tr) = self.transaction {
            rust_async!(py, 
                {
                    self.deletes
                .push(format!("{}/{path}", self.branch).to_string());
            tr.delete(path).await})
        } else {
            Err(PyRuntimeError::new_err("Transaction already committed"))
        }
    }
    pub fn copy(
        &mut self,
        src_branch: &str,
        src_path: &str,
        target_path: &str,
        py: Python<'_>,
    ) -> PyResult<()> {
        if let Some(ref mut tr) = self.transaction {
            self.copies.push((
                format!("{src_branch}/{src_path}").to_string(),
                format!("{}/{target_path}", self.branch).to_string(),
            ));
            rust_async!(py, tr.copy(src_branch, src_path, target_path).await)
        } else {
            Err(PyRuntimeError::new_err("Transaction already committed"))
        }
    }

    pub fn mv(&mut self, src_path: &str, target_path: &str, py: Python<'_>) -> PyResult<()> {
        // can't call this move cos move is taken
        if let Some(ref mut tr) = self.transaction {
            self.moves.push((
                format!("{}/{src_path}", self.branch).to_string(),
                format!("{}/{target_path}", self.branch).to_string(),
            ));
            rust_async!(py, tr.mv(src_path, target_path).await)
        } else {
            Err(PyRuntimeError::new_err("Transaction already committed"))
        }
    }
    pub fn closed(&self) -> PyResult<bool> {
        Ok(self.transaction.is_none())
    }
}

#[pyclass(subclass)]
struct PyWFile {
    writer: Arc<XetWFileObject>,
}

#[pymethods]
impl PyWFile {
    pub fn is_closed(&self, py : Python<'_>) -> PyResult<bool> {
        rust_async!(py, anyhow::Ok(self.writer.is_closed().await))
    }
    pub fn close(&mut self, py : Python<'_>) -> PyResult<()> {
        rust_async!(py, self.writer.close().await)
    }
    pub fn write(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<()> {
        let buf = PyByteArray::from(py, b)?;
        let bufbytes = unsafe { buf.as_bytes() };
        rust_async!(py, self.writer.write(bufbytes).await)
    }
    pub fn readable(&self) -> PyResult<bool> {
        Ok(false)
    }
    pub fn seekable(&self) -> PyResult<bool> {
        Ok(false)
    }
    pub fn writable(&self) -> PyResult<bool> {
        Ok(true)
    }
}
/// This module is implemented in Rust.
#[pymodule]
pub fn rpyxet(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    let cfg = XetConfig::new(None, None, NoPath).unwrap();
    let _ = initialize_tracing_subscriber(&cfg);
    m.add_class::<PyRepoManager>()?;
    m.add_class::<PyRepo>()?;
    m.add_class::<PyWriteTransaction>()?;
    m.add_class::<PyWFile>()?;
    m.add_class::<PyRFile>()?;
    m.add_function(wrap_pyfunction!(configure_login, m)?)?;
    m.add_function(wrap_pyfunction!(perform_mount, m)?)?;
    m.add_function(wrap_pyfunction!(perform_mount_curdir, m)?)?;

    Ok(())
}
