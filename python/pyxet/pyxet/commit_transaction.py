import fsspec
from .url_parsing import parse_url
from .file_interface import XetFile
import sys
import threading
from .rpyxet import rpyxet

TRANSACTION_FILE_LIMIT = 1

def _validate_repo_info_for_transaction(repo_info):
    if repo_info.remote == '':
        raise ValueError("No repository specified")
    if repo_info.branch == '':
        raise ValueError("No branch specified")


class CommitTransaction(fsspec.transaction.Transaction):
    """
    Handles a commit using the transaction interface. A transaction can only
    be performed within the context of a single repository and branch.

    There is a transaction limit of 2048 entries. If the number of changes
    exceed this limit, an automatic commit will be performed.
    """

    def __init__(self, fs, repo_info, commit_message=None):
        """
        This class should not be used directly.
        it is preferred to use fs.transaction.
        """
        _validate_repo_info_for_transaction(repo_info)
        if commit_message is None:
            import datetime
            commit_message = "Commit " + datetime.datetime.now().isoformat()

        self.commit_message = commit_message
        self._transaction_handler = fs._create_transaction_handler(repo_info, commit_message)
        self.fs = fs
        self.repo_info = repo_info

        super().__init__(fs)

    def __repr__(self):
        if self.fs is None:
            return f"Invalidated transaction for {self.repo_info}"
        else:
            return f"Transaction for {self.repo_info}"

    def __str__(self):
        if self.fs is None:
            return f"Invalidated transaction for {self.repo_info}"
        else:
            return f"Transaction for {self.repo_info}"

    def complete(self, commit=True):
        """
        Finalizes and commits or cancels this transaction.
        This transaction object will no longer be usable and is fully detached
        from the originating XetFS object
        """
        if self.fs is None:
            return
        handler = self._transaction_handler
        if handler is not None:
            if commit:
                handler.commit()
            else:
                handler.cancel()

    def open_for_write(self, repo_info):
        assert(repo_info.remote == self.repo_info.remote)
        assert(repo_info.branch == self.repo_info.branch)
        return 

    def copy(self, src_repo_info, dest_repo_info):
        if self.fs is None:
            raise RuntimeError("Transaction object has been invalidated")
        assert(src_repo_info.remote == dest_repo_info.remote)
        assert(dest_repo_info.remote == self.repo_info.remote)
        self._transaction_handler.copy(src_repo_info.branch,
                                       src_repo_info.path,
                                       dest_repo_info.path)

    def rm(self, repo_info):
        if self.fs is None:
            raise RuntimeError("Transaction object has been invalidated")
        assert(repo_info.remote == self.repo_info.remote)
        assert(repo_info.branch == self.repo_info.branch)
        self._transaction_handler.delete(repo_info.path)

    def mv(self, src_repo_info, dest_repo_info):
        if self.fs is None:
            raise RuntimeError("Transaction object has been invalidated")
        assert(src_repo_info.remote == dest_repo_info.remote)
        assert(dest_repo_info.remote == self.repo_info.remote)
        self._transaction_handler.mv(src_repo_info.path, dest_repo_info.path)

    def transaction_size(self):
        return self._transaction_handler.transaction_size()

    def set_ready(self):
        self._transaction_handler.set_ready()


def repo_info_key(repo_info):
    return f"{repo_info.remote}/{repo_info.branch}"

class _TransactionGuard: 

    def __init__(self, tr):
        tr.adjust_access_count(1)
        self.tr = tr 

    def __enter__(self):
        pass

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.tr.adjust_access_count(-1)

class MultiCommitTransaction(fsspec.transaction.Transaction):
    """
    Handles a commit using the transaction interface.
    This transaction handler supports transactions across multiple branches
    by tracking them separately. Simultaneous changes across branches
    will require multiple actual transactions to complete.
    """
    def __init__(self, fs, commit_message=None):
        """
        This class should not be used directly.
        it is preferred to use fs.transaction.
        """

        self.lock = threading.Lock()
        self.commit_message = None
        self._transaction_pool = {}
        self.fs = fs
        self._set_commit_message(commit_message)

        super().__init__(fs)
    
    def set_commit_message(self, commit_message):
        """
        Sets the commit message to be used. This applies to every
        current un-committed transaction and future transactions.
        If commit_message is None, a default message "Commit [current datetime]"
        is used.
        """
        with self.lock:
            self._set_commit_message(commit_message)


    def _set_commit_message(self, commit_message):
        if commit_message is None:
            import datetime
            commit_message = "Commit " + datetime.datetime.now().isoformat()
        self.commit_message = commit_message

    def __repr__(self):
        with self.lock:
            return f"MultiCommitTransaction for [{self._transaction_pool.keys()}]"

    def __str__(self):
        with self.lock:
            return f"MultiCommitTransaction for [{self._transaction_pool.keys()}]"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction and commit, if exit is not due to exception"""
        # only commit if there was no exception
        self.complete(commit=exc_type is None)


    def get_handler_for_repo_info(self, repo_info):
        with self.lock:
            key = repo_info_key(repo_info)

            try:
                tr = self._transaction_pool[key]
            except KeyError:
                tr = self.fs._create_transaction_handler(repo_info, self.commit_message) 
                self._transaction_pool[key] = tr

            return (tr, tr.get_access_token())


    def open_for_write(self, repo_info):
        """
        Opens a file for write. `repo_info` is the result of 
        `pyxet.parse_url(url)`
        """
        handler = self.get_handler_for_repo_info(repo_info)
        return XetFile(handler.open_for_write(repo_info.path), handler)

    def start(self):
        """
        Starts the transaction
        """
        if self.fs.intrans:
            raise RuntimeError("Transaction already in progress")
        self.fs.intrans = True

    def complete(self, commit=True):
        """
        Finalizes and commits or cancels this transaction.
        The transaction can be restarted with start()
        """
        with self.lock:  # Should not be called while other things are in progress, but better be safe.
            ret_except = None
            for k, v in self._transaction_pool.items():
                try:
                    v.complete(commit)
                except Exception as e:
                    sys.stderr.write(f"Failed to commit {k}: {e}\n")
                    sys.stderr.flush()
                    if ret_except is None:
                        ret_except = e
            # reset all the transaction state
            self._transaction_pool = {}
            self.fs.intrans = False
            self._set_commit_message(None)
            if ret_except is not None:
                raise ret_except

    def copy(self, src_repo_info, dest_repo_info):
        """
        Copies a file from src to dest.
        src_repo_info and dest_repo_info are the returned values from
        `pyxet.parse_url(url)`
        """
        handler = self.get_handler_for_repo_info(dest_repo_info)
        handler.copy(src_repo_info, dest_repo_info)

    def mv(self, src_repo_info, dest_repo_info):
        """
        Copies a file from src to dest.
        src_repo_info and dest_repo_info are the returned values from
        `pyxet.parse_url(url)`
        """
        handler = self.get_handler_for_repo_info(dest_repo_info)
        handler.mv(src_repo_info, dest_repo_info)

    def rm(self, repo_info):
        """
        Removes a file.
        repo_info is the return value of `pyxet.parse_url(url)`
        """
        handler = self.get_handler_for_repo_info(repo_info)
        handler.rm(repo_info)

    def _set_do_not_commit(self, flag):
        """
        Internal method for testing purposes.
        Flags all active transactions to not attempt to push
        the commit, but will silently succeed.
        """
        with self.lock:
            for v in self._transaction_pool.values():
                v._transaction_handler.set_do_not_commit(flag)

    def _set_error_on_commit(self, flag):
        """
        Internal method for testing purposes.
        Flags all active transactions to not attempt to push
        the commit, but will just raise an exception
        """
        with self.lock:
            for v in self._transaction_pool.values():
                v._transaction_handler.set_error_on_commit(flag)

    def get_change_list(self):
        deletes = []
        new_files = []
        copies = []
        moves = []
        for v in self._transaction_pool.values():
            deletes.extend(v._transaction_handler.deletes)
            new_files.extend(v._transaction_handler.new_files)
            copies.extend(v._transaction_handler.copies)
            moves.extend(v._transaction_handler.moves)

        return {'deletes': deletes, 'new_files': new_files, 'copies': copies, 'moves':moves}
