use anyhow::anyhow;
use gitxetcore::command::login::*;
use gitxetcore::command::mount::*;
use gitxetcore::command::*;
use gitxetcore::config::ConfigGitPathOption;
use gitxetcore::config::ConfigGitPathOption::NoPath;
use gitxetcore::config::XetConfig;
use gitxetcore::git_integration::git_repo::is_user_identity_set;
use gitxetcore::log::initialize_tracing_subscriber;
use lazy_static::lazy_static;
use pyo3::exceptions::*;
use pyo3::prelude::*;
use pyo3::types::{PyByteArray, PyBytes, PyList};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tokio::sync::{RwLock, RwLockReadGuard, RwLockWriteGuard, Semaphore};
use tracing::{debug, error, info};
use xetblob::*;

lazy_static! {
    static ref MAX_NUM_CONCURRENT_TRANSACTIONS: AtomicUsize = AtomicUsize::new(2);
}

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
            PyRFile::new(self.repo.open_for_read(branch, path).await?)
        )
    }
    pub fn begin_write_transaction(
        &self,
        branch: &str,
        commit_message: &str,
        max_writes_before_commit: usize,
        py: Python<'_>,
    ) -> PyResult<PyWriteTransaction> {
        rust_async!(
            py,
            PyWriteTransaction::new(
                self.repo.clone(),
                branch,
                commit_message,
                max_writes_before_commit
            )
            .await
        )
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
        rust_async!(
            py,
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
    pub fn is_closed(&self) -> PyResult<bool> {
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

lazy_static! {
    /// This is an example for using doc comment attributes
    static ref TRANSACTION_LIMIT_LOCK: Arc<Semaphore> = Arc::new(Semaphore::new((*MAX_NUM_CONCURRENT_TRANSACTIONS).load(Ordering::Relaxed)));
}

struct PyWriteTransactionInternal {
    transaction: XetRepoWriteTransaction,
    branch: String,

    new_files: Vec<String>,
    copies: Vec<(String, String)>,
    deletes: Vec<String>,
    moves: Vec<(String, String)>,

    // A transaction will be cancelled on completion unless
    // this flag is set.
    commit_when_ready: bool,

    // For testing: generate an error on the commit to make sure everything works
    // above this.
    error_on_commit: bool,

    // For testing: go through everything, but don't actually do the last bit of the commit.
    commit_canceled: bool,

    // This happens when
    transaction_complete: bool,

    // The message written on success
    commit_message: String,
    _transaction_permit: tokio::sync::OwnedSemaphorePermit,
}

// This functions as a reference to access the internal transaction object.
// The PyWriteTransaction holds one handle, and each file open for writing
// holds one handle. Once all references are finished, then the transaction
// is either committed or canceled.
//
// The lock inside is an RwLock object so that other objects can quickly check
// whether a transaction has been canceled, allowing errors to propegate correctly.
//
// There are two paths for handles being released: explicitly, with proper error handling
// and reporting, and on drop, where errors are logged and ignored.  This intermediate
// class is needed to properly implement both semantics, so that errors on explicit
// completion propegate properly and transactions are not left in a bad state if there are
// errors elsewhere.
//
#[derive(Clone)]
struct TransactionWriteHandle {
    pwt: Option<Arc<RwLock<PyWriteTransactionInternal>>>,
}

impl TransactionWriteHandle {
    pub fn new(inner: PyWriteTransactionInternal) -> Self {
        Self {
            pwt: Some(Arc::new(RwLock::new(inner))),
        }
    }

    // Convenience functions to acquire locks on the inner objects.
    pub async fn write<'a>(&'a self) -> RwLockWriteGuard<'a, PyWriteTransactionInternal> {
        debug_assert!(self.pwt.is_some());
        self.pwt.as_ref().unwrap().write().await
    }

    pub async fn read<'a>(&'a self) -> RwLockReadGuard<'a, PyWriteTransactionInternal> {
        debug_assert!(self.pwt.is_some());
        self.pwt.as_ref().unwrap().read().await
    }

    // release the handle.
    pub async fn release(&mut self) -> anyhow::Result<()> {
        if let Some(handle) = self.pwt.take() {
            PyWriteTransactionInternal::release_write_handle(handle).await?;
        }
        Ok(())
    }

    // release the handle, setting the target with something new.
    pub async fn release_and_set_transaction(
        &mut self,
        new_pwt: PyWriteTransactionInternal,
    ) -> anyhow::Result<()> {
        self.release().await?;
        self.pwt = Some(Arc::new(RwLock::new(new_pwt)));
        Ok(())
    }
}

impl Drop for TransactionWriteHandle {
    fn drop(&mut self) {
        // This should only occurs in case of errors elsewhere, but must be cleaned up okay.
        if let Some(handle) = self.pwt.take() {
            pyo3_asyncio::tokio::get_runtime().block_on(async {
                let res = PyWriteTransactionInternal::release_write_handle(handle).await;
                if let Err(e) = res {
                    error!("Error deregistering write handle in transaction : {e:?}");
                }
            });
        }
    }
}

impl PyWriteTransactionInternal {
    // Deregister a writer on a successful close by forcing that writer to give
    // back the transaction writing permit.  This allows for proper error propagation
    // when calling close() while ensuring that all combinations of two pathways
    // (Drop or explicit close) to closing a writing never leave the transaction in a
    // bad state.
    async fn release_write_handle(
        handle: Arc<RwLock<PyWriteTransactionInternal>>,
    ) -> anyhow::Result<()> {
        // Only shut down if this is the last reference to self.  This works only if this is the
        // only reference to the PyWriteTransactionInternal
        // object.

        if let Some(s) = Arc::<_>::into_inner(handle) {
            s.into_inner().complete().await?;
        }
        Ok(())
    }

    /// Complete the transaction by either cancelling it or committing it, depending on flags.
    async fn complete(mut self) -> anyhow::Result<()> {
        if self.transaction_complete {
            // This means it was explicitly completed through deregister_write_object,
            // and this is called from the Drop function.
            return Ok(());
        }

        // The function contents can be executed only once, even with errors.
        self.transaction_complete = true;

        if self.error_on_commit {
            return Err(anyhow!("Error on commit flagged; Cancelling."));
        }

        if self.commit_canceled || !self.commit_when_ready {
            info!("PyWriteTransactionInternal::complete: Cancelling commit.");
            self.transaction.cancel().await?;
            return Ok(());
        }

        self.transaction.commit(&self.commit_message).await?;

        Ok(())
    }

    pub fn set_commit_when_ready(&mut self, commit_when_ready: bool) -> anyhow::Result<()> {
        self.commit_when_ready = commit_when_ready;
        Ok(())
    }

    /// This is for testing
    pub fn set_cancel_flag(&mut self, cancel_commit: bool) -> anyhow::Result<()> {
        self.commit_canceled = cancel_commit;
        Ok(())
    }

    /// This is for testing
    pub fn set_error_on_commit(&mut self, error_on_commit: bool) -> anyhow::Result<()> {
        self.error_on_commit = error_on_commit;
        Ok(())
    }

    pub async fn open_for_write(&mut self, path: &str) -> anyhow::Result<Arc<XetWFileObject>> {
        if self.commit_canceled {
            // No point doing anything more.
            return Err(anyhow!(
                "open_for_write failed: Transaction has been canceled."
            ));
        }

        self.new_files
            .push(format!("{}/{path}", self.branch).to_string());
        let writer = self.transaction.open_for_write(path).await?;
        Ok(writer)
    }

    pub async fn transaction_size(&self) -> anyhow::Result<usize> {
        Ok(self.transaction.transaction_size().await)
    }

    pub fn commit_canceled(&self) -> bool {
        self.commit_canceled
    }

    pub async fn delete(&mut self, path: &str) -> anyhow::Result<()> {
        if self.commit_canceled {
            // No point doing anything more.
            return Err(anyhow!("delete failed: Transaction has been canceled."));
        }

        self.transaction.delete(path).await?;
        self.deletes
            .push(format!("{}/{path}", self.branch).to_string());
        Ok(())
    }

    pub async fn copy(
        &mut self,
        src_branch: &str,
        src_path: &str,
        target_path: &str,
    ) -> anyhow::Result<()> {
        if self.commit_canceled {
            // No point doing anything more.
            return Err(anyhow!("copy failed: Transaction has been canceled."));
        }

        self.transaction
            .copy(src_branch, src_path, target_path)
            .await?;
        self.copies.push((
            format!("{src_branch}/{src_path}").to_string(),
            format!("{}/{target_path}", self.branch).to_string(),
        ));
        Ok(())
    }

    pub async fn mv(&mut self, src_path: &str, target_path: &str) -> anyhow::Result<()> {
        if self.commit_canceled {
            // No point doing anything more.
            return Err(anyhow!("mv failed: Transaction has been canceled."));
        }

        self.transaction.mv(src_path, target_path).await?;
        self.moves.push((
            format!("{}/{src_path}", self.branch).to_string(),
            format!("{}/{target_path}", self.branch).to_string(),
        ));
        Ok(())
    }
}

#[pyclass(subclass)]
struct PyWriteTransaction {
    repo: Arc<XetRepo>,
    max_size_before_commit: usize,
    pwt: RwLock<TransactionWriteHandle>,
    branch: String,
    commit_message: String,
}

impl PyWriteTransaction {
    async fn new_transaction(
        repo: &Arc<XetRepo>,
        branch: &str,
        commit_message: &str,
    ) -> anyhow::Result<PyWriteTransactionInternal> {
        let transaction = repo.begin_write_transaction(branch, None, None).await?;

        debug!("PyWriteTransaction::new_transaction(): Acquiring transaction permit.");
        let transaction_permit = TRANSACTION_LIMIT_LOCK.clone().acquire_owned().await?;

        let write_transaction = PyWriteTransactionInternal {
            transaction,
            branch: branch.to_string(),
            commit_message: commit_message.to_string(),
            copies: Vec::new(),
            deletes: Vec::new(),
            moves: Vec::new(),
            new_files: Vec::new(),
            error_on_commit: false,
            commit_when_ready: false,
            _transaction_permit: transaction_permit,
            commit_canceled: false,
            transaction_complete: false,
        };

        Ok(write_transaction)
    }

    async fn new(
        repo: Arc<XetRepo>,
        branch: &str,
        commit_message: &str,
        max_size_before_commit: usize,
    ) -> anyhow::Result<Self> {
        let pwt = Self::new_transaction(&repo, branch, commit_message).await?;

        Ok(Self {
            repo,
            pwt: RwLock::new(TransactionWriteHandle::new(pwt)),
            max_size_before_commit,
            branch: branch.to_string(),
            commit_message: commit_message.to_string(),
        })
    }
}

#[pymethods]
impl PyWriteTransaction {
    /// This is for testing
    pub fn set_cancel_flag(&self, do_not_commit: bool, py: Python<'_>) -> PyResult<()> {
        rust_async!(
            py,
            (self.pwt.read().await.write().await).set_cancel_flag(do_not_commit)
        )
    }

    pub fn set_commit_when_ready(&self, py: Python<'_>) -> PyResult<()> {
        rust_async!(
            py,
            (self.pwt.read().await.write().await).set_commit_when_ready(true)
        )
    }

    /// This is for testing
    pub fn set_error_on_commit(&self, error_on_commit: bool, py: Python<'_>) -> PyResult<()> {
        rust_async!(
            py,
            (self.pwt.read().await.write().await).set_error_on_commit(error_on_commit)
        )
    }

    pub fn open_for_write(&self, path: &str, py: Python<'_>) -> PyResult<PyWFile> {
        rust_async!(py, {
            // Use a write lock here only because we might upgrade this.
            let mut tr_handle_lock = self.pwt.write().await;

            loop {
                let mut pwt_lg = tr_handle_lock.write().await;

                if pwt_lg.transaction_size().await? >= self.max_size_before_commit {
                    pwt_lg.set_commit_when_ready(true)?;

                    drop(pwt_lg); // Release the lock on the actual transaction, since we won't need to access it more.

                    let new_tr =
                        Self::new_transaction(&self.repo, &self.branch, &self.commit_message)
                            .await?;

                    // Release our transaction write handle, setting it to point to the new one
                    tr_handle_lock.release_and_set_transaction(new_tr).await?;

                    // Restarting the loop will now acquire the lock on the new transaction object
                    continue;
                } else {
                    let writer = pwt_lg.open_for_write(path).await?;

                    break anyhow::Ok(PyWFile {
                        writer,
                        transaction_write_handle: tr_handle_lock.clone(),
                    });
                }
            }
        })
    }

    pub fn transaction_size(&self, py: Python<'_>) -> PyResult<usize> {
        rust_async!(
            py,
            (self.pwt.read().await.read().await)
                .transaction_size()
                .await
        )
    }

    pub fn delete(&self, path: &str, py: Python<'_>) -> PyResult<()> {
        rust_async!(py, (self.pwt.read().await.write().await).delete(path).await)
    }

    pub fn copy(
        &self,
        src_branch: &str,
        src_path: &str,
        target_path: &str,
        py: Python<'_>,
    ) -> PyResult<()> {
        rust_async!(
            py,
            (self.pwt.read().await.write().await)
                .copy(src_branch, src_path, target_path)
                .await
        )
    }

    pub fn mv(&self, src_path: &str, target_path: &str, py: Python<'_>) -> PyResult<()> {
        rust_async!(
            py,
            // HMM.  Why does mv take two arguments and copy three?  Where do branches come in here?
            (self.pwt.read().await.write().await)
                .mv(src_path, target_path)
                .await
        )
    }

    #[getter]
    pub fn new_files(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        rust_async!(
            py,
            anyhow::Ok((self.pwt.read().await.read().await).new_files.clone())
        )
    }

    #[getter]
    pub fn copies(&self, py: Python<'_>) -> PyResult<Vec<(String, String)>> {
        rust_async!(
            py,
            anyhow::Ok((self.pwt.read().await.read().await).copies.clone())
        )
    }

    #[getter]
    pub fn deletes(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        rust_async!(
            py,
            anyhow::Ok((self.pwt.read().await.read().await).deletes.clone())
        )
    }

    #[getter]
    pub fn moves(&self, py: Python<'_>) -> PyResult<Vec<(String, String)>> {
        rust_async!(
            py,
            anyhow::Ok((self.pwt.read().await.read().await).moves.clone())
        )
    }
}

#[pyclass(subclass)]
struct PyWFile {
    writer: Arc<XetWFileObject>,
    transaction_write_handle: TransactionWriteHandle,
}

#[pymethods]
impl PyWFile {
    pub fn is_closed(&self, py: Python<'_>) -> PyResult<bool> {
        rust_async!(py, anyhow::Ok(self.writer.is_closed().await))
    }
    pub fn close(&mut self, py: Python<'_>) -> PyResult<()> {
        rust_async!(py, {
            self.writer.close().await?;

            // Give back the handle explicitly in order to ensure errors
            // can get propegated properly here.
            self.transaction_write_handle.release().await
        })
    }

    pub fn write(&mut self, b: &PyAny, py: Python<'_>) -> PyResult<()> {
        let buf = PyByteArray::from(py, b)?;
        let bufbytes = unsafe { buf.as_bytes() };
        rust_async!(py, {
            if self.transaction_write_handle.read().await.commit_canceled() {
                return Err(anyhow!("Write terminated as transaction was canceled."));
            }

            self.writer.write(bufbytes).await
        })
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
