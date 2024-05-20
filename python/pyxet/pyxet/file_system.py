import json
import sys
from urllib.parse import urlparse
from enum import IntEnum

import fsspec
import os

from .commit_transaction import MultiCommitTransaction
from .file_interface import XetFile
from .url_parsing import parse_url, XetPathInfo, normalize_endpoint, set_default_endpoint, get_default_endpoint

if 'SPHINX_BUILD' not in os.environ:
    from .rpyxet import rpyxet

__repo_managers = {}
__login_credentials = {}

def _repo_manager(endpoint):
    global __repo_managers
    global __login_credentials

    endpoint = normalize_endpoint(endpoint)

    try:
        return __repo_managers[endpoint]
    except KeyError:
        pass

    repo = rpyxet.PyRepoManager(endpoint)
    __login_credentials
    if endpoint in __login_credentials:
        repo.override_login_config(*__login_credentials[endpoint])
    elif None in __login_credentials:
        repo.override_login_config(*__login_credentials[None])

    __repo_managers[endpoint] = repo
    return repo


def login(user, token, email=None, host=None):
    """
    Sets the active login credentials used to authenticate against Xethub.
    """
    global __login_credentials
    if host is not None:
        host = normalize_endpoint(host)
        set_default_endpoint(host)
    __login_credentials[host] = (user, token, email, host)
    if host is None:
        for repo in __repo_managers.values():
            repo.override_login_config(user, token, email)
    else:
        if host in __repo_managers:
            __repo_managers[host].override_login_config(user, token, email, host)


def open(file_url, mode="rb", **kwargs):
    """
    Open the file at the specific Xet file URL
    of the form `xet://<endpoint>:<user>/<repo>/<branch>/<path-to-file>`.  

    For example::

        f = pyxet.open('xet://xethub.com:XetHub/Flickr30k/main/results.csv')
    """

    url_info = parse_url(file_url, expect_branch=True)
    fs = XetFS(endpoint = url_info.endpoint)
    return fs._open(url_info.name(), mode=mode, **kwargs)

class XetFSOpenFlags(IntEnum):
    FILE_FLAG_NO_BUFFERING = 0x20000000

class XetFS(fsspec.spec.AbstractFileSystem):
    protocol = "xet"  # This allows pandas, etc. to implement "xet://"

    cachable = True
    sep = "/"
    async_impl = False
    root_marker = "/"

    def from_url(url): 
        """
        Initializes the proper information from a URL.
        """

        url_info = parse_url(url, expect_repo=None)
        return XetFS(endpoint = url_info.endpoint)

    def __init__(self, endpoint=None, **storage_options):
        """
        Opens the repository at `repo_url` as an fsspec file system handle,
        providing read-only operations such as ls, glob, and open.

        User and token are needed for private repositories and they
        can be set with `pyxet.login`.

        Examples::
        
            import pyxet
            fs = pyxet.XetFS('xethub.com')

            # List files.
            fs.ls('XetHub/Flickr30k/main')

            # Read the first 5 lines of a file
            b = fs.open('XetHub/Flickr30k/main/results.csv').read()

        the Xet repository endpoint can be set with the 'endpoint' argument
        or the XET_ENDPOINT environment variable. The default endpoint is
        xethub.com if unspecified
        """
        
        # If the endpoint is None, then it goes to the default xethub.com with a warning
        # later on.
        if endpoint is None:
            self.endpoint = get_default_endpoint()
        else:
            self.endpoint = endpoint

        self.intrans = False
        self._transaction = None

        # Init the base class.
        super().__init__()

    @classmethod
    def _strip_protocol(cls, path):
        """Turn path from fully-qualified to file-system-specific
        May require FS-specific handling, e.g., for relative paths or links.
        """

        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]

        if path.startswith('xet://'):
            protostripped = path[5:]
        elif path.startswith('https://'):
            protostripped = path[8:]
        else:
            protostripped = path
        return protostripped.lstrip('/')

    def get_username(self):
        """
        Returns the inferred username for the endpoint
        """
        return _repo_manager(self.endpoint).get_inferred_username(self.endpoint)

    def unstrip_protocol(self, name):
        """Format FS-specific path to generic, including protocol"""
        return 'xet://' + name.lstrip('/')

    def __repr__(self):
        return f"XetFS(endpoint = {self.endpoint})"

    @staticmethod
    def _get_kwargs_from_urls(path):
        """If kwargs can be encoded in the paths, extract them here
        This should happen before instantiation of the class; incoming paths
        then should be amended to strip the options in methods.
        Examples may look like an sftp path "sftp://user@host:/my/path", where
        the user and host should become kwargs and later get stripped.
        """
        url_path = parse_url(path)
        return {"endpoint" : url_path.endpoint}

    def isdir(self, path):
        """Is this entry directory-like?"""
        return self.isdir_or_branch(path)

    def isdir_or_branch(self, path):
        """Is this entry directory-like?"""
        try:
            t = self.info(path)["type"]
            return t == "directory" or t == "branch"
        except OSError:
            return False

    def branch_info(self, url):
        """
        Returns information about a branch `user/repo/branch` 
        or `xet://[endpoint:]<user>/<repo>/<branch>`
        """
        # try to parse this as a URL
        # and if not try to parse it as a path
        if isinstance(url, XetPathInfo):
            url_path = url
        else:
            url_path = parse_url(url, self.endpoint, expect_branch = True)

        attr = self._manager.stat(url_path.remote(), url_path.branch, "")

        if attr is None:
            raise FileNotFoundError(
                f"Branch or repo not found, remote = {url_path.remote()}, branch = {url_path.branch}")

        return {"name": url_path.name(),
                "size": attr.size,
                "type": attr.ftype}


    def branch_exists(self, url):
        try:
            self.branch_info(url)
            return True
        except Exception as e:
            return False


    def info(self, url):
        """
        Returns information about a path `user/repo/branch/[path]` 
        or `xet://[endpoint:]<user>/<repo>/<branch>/[path]`
        """
        url_path = parse_url(url, self.endpoint, expect_branch = True)
        attr = self._manager.stat(url_path.remote(), url_path.branch, url_path.path)

        if attr is None:
            raise FileNotFoundError(f"File not found {url}")

        return {"name": url_path.name(),
                "size": attr.size,
                "type": attr.ftype,
                "last_modified": None if len(attr.last_modified) == 0 else attr.last_modified}

    def make_repo(self, dest_path, private=False, **kwargs):
        dest = parse_url(dest_path, self.endpoint, expect_branch = False, expect_repo=True)
        if self.is_repo(dest_path):
            raise ValueError(f"{dest_path} already exists")

        query = json.dumps({'name': dest.repo, 'owner': dest.user, 'private': private})
        ret = json.loads(bytes(self._manager.api_query(dest.endpoint_url(), "", "post", query)))
        return ret

    def fork_repo(self, origin_path, dest_path, **kwargs):
        origin = parse_url(origin_path, self.endpoint, expect_branch = False)
        dest = parse_url(dest_path, self.endpoint, expect_branch = False)
        if not self.is_repo(origin_path):
            raise ValueError(f"{origin_path} is not a repo")
        if self.is_repo(dest_path):
            raise ValueError(f"{dest_path} already exists")
        if origin.endpoint != dest.endpoint:
            raise ValueError("Cannot fork repos between endpoints.")

        auth_user = self.get_username()
        if dest.user != auth_user: 
            raise ValueError(f"Can only fork a repo into your account ({dest.user} != {auth_user})")

        query = json.dumps({'name': dest.repo})
        ret = json.loads(bytes(self._manager.api_query(origin.remote(), "forks", "post", query)))
        return ret

    def duplicate_repo(self, origin_path, dest_path, **kwargs):
        origin = parse_url(origin_path, self.endpoint, expect_branch = False)
        dest = parse_url(dest_path, self.endpoint, expect_branch = False)
        
        if not self.is_repo(origin.remote()):
            raise ValueError(f"{origin_path} is not a repo")
        if self.is_repo(dest.remote()):
            raise ValueError(f"{dest_path} already exists")
        if origin.endpoint != dest.endpoint:
            raise ValueError("Cannot fork repos between different endpoints.")
        
        auth_user = self.get_username()
        if dest.user != auth_user: 
            raise ValueError(f"Can only duplicate a repo into your account ({dest.user} != {auth_user})")

        ret = json.loads(bytes(self._manager.api_query(origin.remote(), "duplicate", "post", "")))

        if 'full_name' not in ret:
            raise RuntimeError("Duplication failed")
        ret_name = 'xet://' + ret['full_name']
        ret_info = parse_url(ret_name, self.endpoint, expect_branch=False)
        if ret_info == dest:
            return ret

        return self.rename_repo(ret_name, dest_path)

    def rename_repo(self, origin_path, dest_path, **kwargs):
        origin = parse_url(origin_path, self.endpoint, expect_branch = False)
        dest = parse_url(dest_path, self.endpoint, expect_branch = False)
        
        if not self.is_repo(origin.remote()):
            raise ValueError(f"{origin_path} is not a repo")
        if self.is_repo(dest.remote()):
            raise ValueError(f"{dest_path} already exists")

        if origin.user != dest.user:
            raise ValueError("Username must be the same between source and destination")

        query = json.dumps({'name': dest.repo})
        ret = json.loads(bytes(self._manager.api_query(origin.remote(), "", "patch", query)))
        return ret

    def set_repo_attr(self, origin_path, attrkey, attrvalue, **kwargs):
        origin = parse_url(origin_path, self.endpoint, expect_branch=False)
        if not self.is_repo(origin_path):
            raise ValueError(f"{origin_path} is not a repo")

        query = json.dumps({attrkey: attrvalue})
        ret = json.loads(bytes(self._manager.api_query(origin.remote(), "", "patch", query)))
        return ret

    def list_repos(self, url, raw=False, **kwargs):
        """
        Lists the repos available for a path of the form `user` or `xet://[endpoint:]<user>`
        """
        remote = parse_url(url, self.endpoint, expect_branch=False, expect_repo=False)

        res = json.loads(bytes(self._manager.api_query(remote.remote(endpoint_only=True), "", "get", "")))
        if raw:
            return res
        else:
            return [{'name': f['full_name'],
                     'permissions': f['permissions']} for f in res]

    def list_branches(self, path, raw=False, **kwargs):
        """
        Lists the branches for a path of the form `user/repo` or `xet://[endpoint:]<user>/<repo>`
        """
        url_path = parse_url(path, self.endpoint, expect_branch=False)
        res = json.loads(bytes(self._manager.api_query(url_path.remote(), "branches", "get", "")))

        if raw:
            return res
        else:
            return [{'name': r['name'], 'type': 'branch'} for r in res]

    def update_size(self, path, bucket_size):
        """
        Calls Xetea to update the size of a synchronized S3 bucket for the repo.
        """
        url_path = parse_url(path, self.endpoint, expect_branch=True)
        
        body = json.dumps({
            'size': bucket_size,
            'branch': url_path.branch
        })
        self._manager.api_query(url_path.remote(), "remote_size", "post", body)

    def ls(self, path : str, detail=True, **kwargs):
        """List objects at path.
        This should include subdirectories and files at that location. The
        difference between a file and a directory must be clear when details
        are requested.
        The specific keys, or perhaps a FileInfo class, or similar, is TBD,
        but must be consistent across implementations.
        Must include:

        - full path to the entry (without protocol)
        - size of the entry, in bytes. If the value cannot be determined, will
          be ``None``.
        - type of entry, "file", "directory" or other

        Additional information
        may be present, appropriate to the file-system, e.g., generation,
        checksum, etc.
        May use refresh=True|False to allow use of self._ls_from_cache to
        common where listing may be expensive.

        Parameters:

            path: str
            detail: bool
                if True, gives a list of dictionaries, where each is the same as
                the result of ``info(path)``. If False, gives a list of paths
                (str).
            kwargs: may have additional backend-specific options, such as version
                information

        Returns:
            List of strings if detail is False, or list of directory information
            dicts if detail is True.  These dicts would have: name (full path in the FS), 
            size (in bytes), type (file, directory, or something else) and other FS-specific keys.
        """

        url_path = parse_url(path, self.endpoint, expect_branch=None, expect_repo=None)

        if url_path.repo == "":
            names = [f['name'] for f in self.list_repos(path)]

            # To list all repos accessible by the current authenticated user, use 
            # xet://endpoint:/
            if url_path.user == "":
                return [{'name': url_path.endpoint + ":" + n, 'type': 'repo'} for n in names]
            else:
                return [{'name': url_path.endpoint + ":" + n, 'type': 'repo'} for n in names if n.startswith(url_path.user)]

        elif url_path.branch == "":
            branches = self.list_branches(url_path.remote())
            return [{'name':  url_path.base_path() + "/" + n['name'], 'type': 'branch'} for n in branches]
        else:
            files, file_info = self._manager.listdir(url_path.remote(),
                                                     url_path.branch,
                                                     url_path.path)

        # Note that we cannot actually standardize the paths in the listed files.  
        # If we do, glob will not work as it calls this and matches names against the query.
        if detail:
            ret = [{"name": url_path.base_path() + "/" + fname, 
                     "size": finfo.size,
                     "type": finfo.ftype}
                    for fname, finfo in zip(files, file_info)]
        else:
            ret = [url_path.base_path() + "/" + fname for fname in files]

        return ret

    def _open(
            self,
            path,
            mode="rb",
            **kwargs,
    ):
        """
        Return raw bytes-mode file-like from the file-system.

        Reads can be performed from any where, but writes must be performed
        within the context of a transaction which must be scoped to within a
        single repository branch.
        """

        url_path = parse_url(path, self.endpoint)

        transaction = getattr(self, "_transaction", None)

        if transaction is None and not mode.startswith('r'):
            raise RuntimeError(
                "Write access to files is only allowed within a commit transaction.")

        if not mode.startswith('r'):
            # this is a write
            if self._transaction is None:
                # with no transaction
                raise RuntimeError("Write only allowed in the context of a commit transaction."
                                   "Use `with fs.transaction(repo_and_branch, [commit_message]):` to enable write access.")

        if mode.startswith('r'):
            repo_handle = self._manager.get_repo(url_path.remote())
            branch = url_path.branch
            if "flags" in kwargs:
                handle = repo_handle.open_for_read_with_flags(branch, url_path.path, kwargs["flags"])
            else:
                handle = repo_handle.open_for_read(branch, url_path.path)
            return XetFile(handle)
        elif mode.startswith('w'):
            return self._transaction.open_for_write(url_path)
        else:
            raise ValueError("Mode '%s' not supported.", mode)

    def set_commit_message(self, message):
        """
        Sets the commit message on the active transaction
        """
        if self._transaction is None:
            raise RuntimeError("No active transaction")
        self._transaction.set_commit_message(message)

    def rm(self, path, *args, **kwargs):
        """
        Delete a file.

        Deletions must be performed within the context of a transaction 
        which must be scoped to within a single repository branch.
        """
        transaction = self._transaction

        if transaction is None:
            raise RuntimeError(
                "Write access to files is only allowed within a commit transaction.")

        if len(args) > 0:
            print(f"rm arguments {args} ignored", file=sys.stderr)
        if len(kwargs) > 0:
            print(f"rm arguments {kwargs} ignored", file=sys.stderr)

        path = parse_url(path, self.endpoint, expect_repo = None)
        if len(path.path) == 0 and len(path.branch) > 0:
            raise ValueError("Cannot delete branches with 'rm'")
        if len(path.path) == 0 and len(path.branch) == 0:
            raise ValueError("Cannot delete repositories with 'rm'")

        transaction.rm(path)

    def is_repo(self, path):
        """
        Returns true if the path is a repo
        """
        url_path = parse_url(path, self.endpoint, expect_branch=False)
        try:
            self.list_branches(url_path.remote())
            return True
        except Exception as e:
            return False

    def make_branch(self, repo, src_branch_name, target_branch_name):
        """
        Creates a branch in a repo
        """
        if not self.is_repo(repo):
            raise ValueError(f"{repo} is not a repository")

        has_src_branch = self.branch_exists(repo + "/" + src_branch_name)
        if has_src_branch is False:
            raise ValueError(f"Cannot copy branch as source branch does not exist: {src_branch_name}")
        has_dest_branch = self.branch_exists(repo + "/" + target_branch_name)
        if has_dest_branch:
            raise ValueError(f"Cannot copy branch as destination branch already exists: {target_branch_name}")

        query = {"new_branch_name": target_branch_name,
                 "old_branch_name": src_branch_name}
        query = json.dumps(query)
        url_path = parse_url(repo, self.endpoint)
        self._manager.api_query(url_path.remote(), "branches", "post", query)

    def find_ref(self, repo, ref_name):
        if not self.is_repo(repo):
            raise ValueError(f"{repo} is not a repository")
        url_path = parse_url(repo, self.endpoint)
        res = self._manager.api_query(url_path.remote(), f"git/refs/{ref_name}", "get", "")
        return json.loads(bytes(res))

    def delete_branch(self, repo, branch_name):
        """
        deletes a branch in a repo
        """
        if not self.is_repo(repo):
            raise ValueError(f"{repo} is not a repository")

        has_branch = self.branch_exists(repo + "/" + branch_name)
        if has_branch is False:
            raise ValueError(f"Cannot delete branch as branch does not exist: {branch_name}")

        if branch_name == 'main':
            raise ValueError("Cannot delete main branch")

        url_path = parse_url(repo, self.endpoint)
        self._manager.api_query(url_path.remote(), f"branches/{branch_name}", "delete", "")

    def cp_file(self, path1, path2, *args, **kwargs):
        """
        Copies a file or directory from a xet path to another xet path.

        Copies must be performed within the context of a transaction
        and are allowed to span branches
        """
        transaction = self._transaction
        if len(args) > 0:
            print(f"cp arguments {args} ignored", file=sys.stderr)
        if len(kwargs) > 0:
            print(f"cp arguments {kwargs} ignored", file=sys.stderr)

        if transaction is None:
            raise RuntimeError(
                "Write access to files is only allowed within a commit transaction.")
        parsed_path1 = parse_url(path1, self.endpoint)
        parsed_path2 = parse_url(path2, self.endpoint)
        if parsed_path1.remote() != parsed_path2.remote():
            raise ValueError("Can only copy between paths in the same repository")
        if len(parsed_path1.branch) == 0:
            raise ValueError(f"Branch not specified in copy source {path1}")
        if len(parsed_path2.branch) == 0:
            raise ValueError(f"Branch not specified in copy dest {path2}")

        if len(parsed_path1.path) == 0 and len(parsed_path2.path) == 0:
            query = {"new_branch_name": parsed_path2.branch,
                     "old_branch_name": parsed_path1.branch}
            query = json.dumps(query)
            self._manager.api_query(parsed_path1.remote(), "branches", "post", query)
            return

        transaction.copy(parsed_path1, parsed_path2)

    def mv(self, path1, path2, *args, **kwargs):
        """
        Moves a file or directory from a xet path to another xet path.

        Moves must be performed within the context of a transaction 
        and must be within the same branch
        """
        transaction = self._transaction
        if len(args) > 0:
            print(f"move arguments {args} ignored", file=sys.stderr)
        if len(kwargs) > 0:
            print(f"move arguments {kwargs} ignored", file=sys.stderr)

        if transaction is None:
            raise RuntimeError(
                "Write access to files is only allowed within a commit transaction.")
        parsed_path1 = parse_url(path1, self.endpoint, expect_branch=True)
        parsed_path2 = parse_url(path2, self.endpoint, expect_branch=True)
        if parsed_path1.remote() != parsed_path2.remote():
            raise ValueError("Can only copy between paths in the same repository")
        if parsed_path1.branch != parsed_path2.branch:
            raise ValueError("Moves can only happen within a branch")

        transaction.mv(parsed_path1, parsed_path2)

    def move(self, path1, path2, *args, **kwargs):
        return self.mv(path1, path2, *args, **kwargs)

    def add_deduplication_hints(self, path_urls):
        """
        Fetches and downloads all of the metadata needed for binary deduplication against 
        all the paths given by `paths`.  Once fetched, new data will be deduplicated against 
        any binary content given by `paths`.  
        """
        if isinstance(path_urls, str):
            path_urls = [path_urls]
        url_paths = [parse_url(url, self.endpoint) for url in path_urls]

        self._add_deduplication_hints_by_url(url_paths)

    def _add_deduplication_hints_by_url(self, url_paths, min_dedup_byte_threshhold=None):

        if min_dedup_byte_threshhold is None:
            # TODO: set this to a more resonable value.  
            min_dedup_byte_threshhold = 0

        paths_by_remotes = {}
        for url in url_paths:
            paths_by_remotes.setdefault(url.remote(), []).append(url)

        for (remote, urls) in paths_by_remotes.items():
            repo_handle = self._manager.get_repo(remote)

            repo_handle.fetch_hinted_shards_for_dedup([(url.branch, url.path) for url in urls],
                                                      min_dedup_byte_threshhold)

    @property
    def _manager(self):
        """
        The repo manager associated with this repo.
        """
        return _repo_manager(self.endpoint)


    @property
    def transaction(self):
        """
        Begin a transaction context for a given repository and branch.
        The entire transaction is committed atomically at the end of the 
        transaction. All writes must be performed into this branch::

            with fs.transaction as tr:
                tr.set_commit_message("message")
                file = fs.open('<user>/<repo>/main/hello.txt','w')
                file.write('hello world')
                file.close()

        The transaction object is an instance of the :class:`MultiCommitTransaction`
        """
        if self._transaction is None:
            self._transaction = MultiCommitTransaction(self)
        return self._transaction

    def _create_transaction_handler(self, repo_info, commit_message):
        """
        Internal method used by CommitTransaction to get
        a transaction handler object from the repository handle
        """
        repo_handle = self._manager.get_repo(repo_info.remote())
        return repo_handle.begin_write_transaction(repo_info.branch, commit_message)

    def start_transaction(self, commit_message=None):
        """
        Begin a write transaction for a repository and branch.
        The entire transaction is committed atomically at the end of the
        transaction. All writes must be performed into this branch

        repo_and_branch is of the form
        `<user>/<repo>/<branch>` or `xet://[endpoint:]<user>/<repo>/<branch>`::

            fs.start_transaction('my commit message')
            file = fs.open('user/repo/main/hello.txt','w')
            file.write('hello world')
            file.close()
            fs.end_transaction()

        The transaction object is an instance of the :class:`MultiCommitTransaction`
        """
        tr = self.transaction
        tr.start()
        tr.set_commit_message(commit_message)
        return tr

    def cancel_transaction(self):
        """Cancels any active transactions. non-context version"""
        self._transaction.complete(False)

    def end_transaction(self):
        """Finish write transaction, non-context version. See :func:`start_transaction`"""
        self._transaction.complete()

    def mkdir(path, *args, **kwargs):
        """Noop. Empty directories cannot be created"""
        pass

    def mkdirs(path, *args, **kwargs):
        """Noop. Empty directories cannot be created"""
        pass

    def makedir(path, *args, **kwargs):
        """Noop. Empty directories cannot be created"""
        pass

    def makedirs(path, *args, **kwargs):
        """Noop. Empty directories cannot be created"""
        pass


fsspec.register_implementation("xet", XetFS, clobber=True)
