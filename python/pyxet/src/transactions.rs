use std::sync::atomic::{AtomicUsize, Ordering};

use anyhow::{anyhow, Result};
use lazy_static::lazy_static;
use std::sync::Arc;
use tokio::sync::{RwLock, RwLockReadGuard, RwLockWriteGuard, Semaphore};
use tracing::{debug, error, info};
use xetblob::*;

lazy_static! {
    static ref MAX_NUM_CONCURRENT_TRANSACTIONS: AtomicUsize = AtomicUsize::new(2);

    /// This is an example for using doc comment attributes
    static ref TRANSACTION_LIMIT_LOCK: Arc<Semaphore> = Arc::new(Semaphore::new((*MAX_NUM_CONCURRENT_TRANSACTIONS).load(Ordering::Relaxed)));
}

pub struct WriteTransaction {
    transaction: XetRepoWriteTransaction,
    branch: String,

    pub new_files: Vec<String>,
    pub copies: Vec<(String, String)>,
    pub deletes: Vec<String>,
    pub moves: Vec<(String, String)>,

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

impl WriteTransaction {
    pub async fn new(repo: &Arc<XetRepo>, branch: &str, commit_message: &str) -> Result<Self> {
        let transaction = repo.begin_write_transaction(branch, None, None).await?;

        debug!("PyWriteTransaction::new_transaction(): Acquiring transaction permit.");
        let transaction_permit = TRANSACTION_LIMIT_LOCK.clone().acquire_owned().await?;

        let write_transaction = Self {
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

    /// Complete the transaction by either cancelling it or committing it, depending on flags.
    pub async fn complete(mut self) -> Result<()> {
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
        } else {
            self.transaction.commit(&self.commit_message).await?;
        }

        Ok(())
    }

    pub fn set_commit_when_ready(&mut self, commit_when_ready: bool) -> Result<()> {
        self.commit_when_ready = commit_when_ready;
        Ok(())
    }

    /// This is for testing
    pub fn set_cancel_flag(&mut self, cancel_commit: bool) -> Result<()> {
        self.commit_canceled = cancel_commit;
        Ok(())
    }

    /// This is for testing
    pub fn set_error_on_commit(&mut self, error_on_commit: bool) -> Result<()> {
        self.error_on_commit = error_on_commit;
        Ok(())
    }

    pub async fn open_for_write(&mut self, path: &str) -> Result<Arc<XetWFileObject>> {
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

    pub async fn transaction_size(&self) -> Result<usize> {
        Ok(self.transaction.transaction_size().await)
    }

    pub fn commit_canceled(&self) -> bool {
        self.commit_canceled
    }

    pub async fn delete(&mut self, path: &str) -> Result<()> {
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
    ) -> Result<()> {
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

    pub async fn mv(&mut self, src_path: &str, target_path: &str) -> Result<()> {
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

    // Deregister a writer on a successful close by forcing that writer to give
    // back the transaction writing permit.  This allows for proper error propagation
    // when calling close() while ensuring that all combinations of two pathways
    // (Drop or explicit close) to closing a writing never leave the transaction in a
    // bad state.
    pub async fn release_write_handle(handle: Arc<RwLock<WriteTransaction>>) -> Result<()> {
        // Only shut down if this is the last reference to self.  This works only if this is the
        // only reference to the PyWriteTransactionInternal
        // object.

        if let Some(s) = Arc::<_>::into_inner(handle) {
            s.into_inner().complete().await?;
        }
        Ok(())
    }
}
