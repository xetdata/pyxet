import pyxet
import re
import contextlib


class Path:

    def __init__(self, path: str):
        self.path = path
        self.info = pyxet.info(path, allow_empty_path=True, exist_ok=True)
        self.type = self.info.get('type', None)
        self.size = self.info.get('size', 0)
        with contextlib.suppress(ValueError):
            remote, user, repo, branch, path = pyxet._parse_path(self.path, allow_empty_path=True)
            self.info['remote'] = remote
            self.info['user'] = user
            self.info['repo'] = repo
            self.info['branch'] = branch
            self.info['path'] = path

    @property
    def repo(self):
        return self.info.get('repo', None)

    @property
    def user(self):
        return self.info.get('user', None)

    @property
    def branch(self):
        return self.info.get('branch', None)

    @property
    def remote(self):
        return self.info.get('remote', None)

    @property
    def name(self):
        split = self.path.split('/')
        if len(split) == 0:
            return ''
        return split[-1]

    def __str__(self):
        return self.path

    def __repr__(self):
        return f"XetPath({self.path})"

    @property
    def is_xet(self):
        return self.info != {}

    def read_text(self):
        with pyxet.open(self.path) as f:
            return f.readall().decode()

    def read_bytes(self):
        with pyxet.open(self.path) as f:
            return f.readall()

    # TODO important
    def write_text(self, text: str):
        raise NotImplementedError()

    # TODO important
    def write_bytes(self, bytes: bytes):
        raise NotImplementedError()

    # TODO
    def stat(self):
        """
        return os.stat_result with the following attributes:
        st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime
        """
        raise NotImplementedError()

    # TODO - low priority
    def replace(self, target: str):
        """
        Rename this path to the target path, overwriting if that path exists.

        The target path may be absolute or relative. Relative paths are
        interpreted relative to the current working directory, *not* the
        directory of the Path object.

        Returns the new Path instance pointing to the target path.
        """
        raise NotImplementedError()

    # TODO - high priority
    def unlink(self):
        """
        Remove this file or link.
        If the path is a directory, use rmdir() instead.
        """
        raise NotImplementedError()

    def glob(self, pattern: str):
        import pyxet.glob
        return pyxet.glob.glob(f"{self.path}/{pattern}")

    def exists(self):
        return self.info != {}

    def home(self):
        if self.is_xet:
            return Path('/'.join([self.remote, self.user, self.repo, self.branch]))

    # TODO - change if we deal with relative paths
    def absolute(self):
        return Path(self.path)

    # TODO - change if we deal with relative paths
    def is_absolute(self):
        return True

    def is_dir(self):
        return self.type == 'directory'

    def is_file(self):
        return self.type == 'file'

    # TODO - low priority
    def is_fifo(self):
        """
        Whether this path is a FIFO.
        """
        raise NotImplementedError

    def is_mount(self):
        raise NotImplementedError()

    def iterdir(self):
        from pyxet.glob import _listdir
        for path in _listdir(self.path):
            yield Path(path)

    def joinpath(self, path: str):
        return Path('/'.join([self.path, path]))

    # TODO - low priority
    def lstat(self):
        raise NotImplementedError()

    # TODO
    def samefile(self, path: str):
        """
        Probably needed to compare local and cloud versions of the same file
        @param path:
        @return:
        """
        raise NotImplementedError()

    def match(self, pattern: str):
        return re.match(pattern, self.path)

    # TODO - important
    def mkdir(self, mode: int, parents: bool, exist_ok: bool):
        raise NotImplementedError()

    # TODO - important
    def rmdir(self):
        raise NotImplementedError()

    def with_name(self, name: str):
        return self.parent().joinpath(name)

    def with_suffix(self, suffix: str):
        raise NotImplementedError()

    def with_stem(self, stem: str):
        raise NotImplementedError()

    @property
    def parent(self):
        split = self.path.split('/')
        if len(split) == 0:
            return Path(self.repo)
        return Path('/'.join(split[:-1]))

    # TODO unclear if relevant
    def parents(self):
        raise NotImplementedError()

    # TODO - low priority
    def touch(self):
        raise NotImplementedError()

    # TODO unclear if relevant
    @property
    def root(self):
        return ""
