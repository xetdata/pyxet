import rpyxet
import io
import fsspec

_repo_pool = {}


def _parse_path(url, allow_empty_path=False):
    expected_path_components = 4
    if allow_empty_path:
        expected_path_components = 3

    path = ""
    if url.startswith("http://") or url.startswith("https://"):
        from urllib.parse import urlparse
        parse = urlparse(url)
        # the first path component is empty as parse.path begins with '/'
        pathsplit = parse.path.split('/')[1:]
        if len(pathsplit) < expected_path_components:
            raise ValueError("URL must be of the form"
                             "https://xethub.com/user/repo.git/branch/path")
        user = pathsplit[0]
        repo = pathsplit[1]
        branch = pathsplit[2]
        if len(pathsplit) >= 4:
            path = '/'.join(pathsplit[3:])
        remote = parse.scheme + "://" + parse.netloc
    elif url.startswith("xet@") or url.startswith("git@"):
        urlsplit = url.split(':')
        if len(urlsplit) != 2:
            raise ValueError("SSH URL must be of the form"
                             "xet@xethub.com:username/repo.git/branch/path")
        remote = urlsplit[0]  # xet@xethub.com
        pathsplit = urlsplit[1].split('/')
        if len(pathsplit) < expected_path_components:
            raise ValueError("URL must be of the form"
                             "xet@xethub.com:username/repo.git/branch/path")
        user = pathsplit[0]
        repo = pathsplit[1]
        branch = pathsplit[2]
        if len(pathsplit) >= 4:
            path = '/'.join(pathsplit[3:])
    else:
        raise ValueError("URL must be a http/https or a SSH path")

    if not repo.endswith(".git"):
        raise ValueError("Repo is expected to end with .git")

    return (remote, user, repo, branch, path)


def open(url):
    """
    Opens a xet file in a Xet repo.
    URL is a complete path of the form:
      xet@xethub.com:username/repo.git/branch/path...
    or https://xethub.com/user/repo.git/branch/path
    """
    remote, user, repo, branch, path = _parse_path(url)
    if not repo.endswith(".git"):
        raise ValueError("Repo is expected to end with .git")

    repo_key = '/'.join([remote, user, repo])
    if repo_key not in _repo_pool:
        _repo_pool[repo_key] = rpyxet.PyRepo(repo_key)

    return XetFile(_repo_pool[repo_key].open(branch, path))


def info(url, allow_empty_path=False, exist_ok=False):
    try:
        remote, user, repo, branch, path = _parse_path(url, allow_empty_path=allow_empty_path)
        repo_key = '/'.join([remote, user, repo])
        if repo_key not in _repo_pool:
            _repo_pool[repo_key] = rpyxet.PyRepo(repo_key)
        stat = _repo_pool[repo_key].stat(branch, path)
    except (ValueError, OSError) as e:
        if not exist_ok:
            raise e
        return {}
    return {"type": stat.ftype,
            "size": stat.size,
            "name": "/".join([repo, branch, path])}


def ls(url, detail=False, exist_ok=False):
    try:
        remote, user, repo, branch, path = _parse_path(url, True)
        repo_key = '/'.join([remote, user, repo])
        if repo_key not in _repo_pool:
            _repo_pool[repo_key] = rpyxet.PyRepo(repo_key)
        names, listing = _repo_pool[repo_key].readdir(branch, path)
        """
        if len(path) == 0:
            prefix = "/".join([repo, branch])
        else:
            prefix = "/".join([repo, branch, path])
        """
    except (ValueError, OSError) as e:
        if not exist_ok:
            raise e
        return []

    if detail is False:
        return names
    return [{"type": stat.ftype,
             "size": stat.size,
             "name": name} for (name, stat) in zip(names, listing)]


class XetFile(io.RawIOBase):
    """
    A file in a Xet repo
    """

    def __init__(self, pyxethandle):
        super().__init__()
        self.handle = pyxethandle

    def close(self):
        return self.handle.close()

    @property
    def closed(self):
        return self.handle.closed

    def fileno(self):
        raise OSError("No file descriptor")

    def flush(self):
        pass

    def isatty(self):
        return False

    def readable(self):
        return True

    def seekable(self):
        return True

    def writable(self):
        return False

    def readline(self, size=-1):
        if size is None:
            return self.handle.readline(-1)
        if isinstance(size, int):
            return self.handle.readline(size)
        raise TypeError("size must be an integer")

    def readlines(self, hint=-1):
        if hint is None:
            return self.handle.readlines(-1)

        if isinstance(hint, int):
            return self.handle.readlines(hint)

        raise TypeError("hint must be an integer")

    def seek(self, offset, whence=io.SEEK_SET):
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END):
            raise ValueError("Unexpected value for whence")
        if not isinstance(offset, int):
            raise TypeError("Unexpected type for offset")

        return self.handle.seek(offset, whence)

    def tell(self):
        return self.handle.tell()

    def read(self, size=-1):
        if not isinstance(size, int):
            raise TypeError("Unexpected type for size")
        return self.handle.read(size)

    def readall(self):
        return self.handle.readall()

    def readinto(self, b):
        return self.handle.readinto(b)

    def readinto1(self, b):
        return self.handle.readinto1(b)


class XetFS(fsspec.spec.AbstractFileSystem):
    def __init__(self):
        super().__init__()

    def open(self, url, mode='rb', block_size=None, cache_options=None, compression=None):
        return open(url)

    def info(self, url):
        return info(url)

    def stat(self, url):
        return info(url)

    def ls(self, url):
        return ls(url)


fsspec.register_implementation('xet', XetFS)
from pyxet.arrow import read_arrow
