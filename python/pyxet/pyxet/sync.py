from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pyxet.util import _ltrim_match, _get_fs_and_path, _single_file_copy, _isdir

XET_MTIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class SyncCommand:

    def __init__(self, source, destination, message, dryrun):
        self._message = message
        self._dryrun = dryrun
        self._src_fs, self._src_proto, self._src_root = _get_normalized_fs_protocol_and_path(source)
        self._dest_fs, self._dest_proto, self._dest_root = _get_normalized_fs_protocol_and_path(destination)
        self._files_synced = 0

    def validate(self):
        """
        Performs early validation for the source and destination paths of
        a xet sync. Doesn't catch all failure conditions, but catches many
        of the easy validations.

        Raises exceptions on failure
        """

        print(f"Checking sync")
        if self._dest_proto != 'xet':
            raise ValueError(f"Unsupported destination protocol: {self._dest_proto}, only xet:// targets are supported")
        if self._src_proto == 'xet':
            raise ValueError(f"Unsupported source protocol: {self._src_proto}, only non-xet sources are supported")

        # check that the destination specifies an existing branch
        # TODO: we may want to be able to sync remote location to a new branch?
        self._dest_fs.branch_info(self._dest_root)

        # source should be a directory
        if not _isdir(self._src_fs, self._src_root):
            raise ValueError(f"source: {self._src_root} needs to be a directory")

        # wildcards not supported
        if '*' in self._src_root or '*' in self._dest_root:
            raise ValueError(f"Wildcards not supported in paths")

    def run(self):
        """
        Runs this Sync command.
        """
        print(f"Starting sync")
        failed_copies = []

        if not self._dryrun:
            self._dest_fs.start_transaction(self._message)
        with ThreadPoolExecutor() as executor:
            futures = []
            self._sync_dir(executor, futures, failed_copies, self._src_root, self._dest_root)

            # Waiting for all copy jobs to complete
            for future in futures:
                try:
                    future.result()
                    self._files_synced = self._files_synced + 1
                except Exception as e:
                    print(f"Error: {e}")
                    failed_copies.append("")

        if not self._dryrun:
            self._dest_fs.end_transaction()
            print(f"Completed sync. Copied: {self._files_synced} files")
            if len(failed_copies) > 0:
                print(f"{len(failed_copies)} entries failed to copy")

    def _sync_dir(self, executor, futures, failed_copies, src_path, dest_path):
        for src_info in self._src_fs.ls(src_path, detail=True):
            abs_path = src_info['name']
            rel_path = _ltrim_match(abs_path, src_path).lstrip('/')
            dest_for_this_path = _join_to_absolute(dest_path, rel_path)

            try:
                dest_info = self._dest_fs.info(dest_for_this_path)
            except FileNotFoundError:
                dest_info = None

            if dest_info is not None and src_info['type'] != dest_info['type']:
                failed_copies.append(rel_path)
                print(f"Copy failed: {src_path} is a {src_info['type']}, {dest_path} is a {dest_info['type']}")
                continue

            size = src_info.get('size', None)

            if dest_info is None:
                # copy src to dest
                if src_info['type'] == 'directory':
                    self._copy_dir_async(executor, futures, abs_path, dest_for_this_path)
                else:
                    self._copy_file_async(executor, futures, abs_path, dest_for_this_path, size)
            elif src_info['type'] == 'directory':
                # recursively sync src -> dest
                self._sync_dir(executor, futures, failed_copies, abs_path, dest_for_this_path)
            elif _should_sync(self._src_proto, src_info, self._dest_proto, dest_info):
                # copy src to dest
                self._copy_file_async(executor, futures, abs_path, dest_for_this_path, size)

    def _copy_dir_async(self, executor, futures, src_path, dest_path):
        for abs_path, info in self._src_fs.find(src_path, detail=True).items():
            rel_path = _ltrim_match(abs_path, src_path).lstrip('/')
            dest_for_this_path = _join_to_absolute(dest_path, rel_path)

            # Create parent directories in destination
            if not self._dryrun:
                dest_dir = '/'.join(dest_for_this_path.split('/')[:-1])
                self._dest_fs.makedirs(dest_dir, exist_ok=True)

            # Submitting copy job to thread pool
            size = info.get('size', None)
            self._copy_file_async(executor, futures, abs_path, dest_for_this_path, size)

    def _copy_file_async(self, executor, futures, src_path, dest_path, size):
        if not self._dryrun:
            futures.append(
                executor.submit(
                    _single_file_copy,
                    self._src_fs,
                    src_path,
                    self._dest_fs,
                    dest_path,
                    size_hint=size
                ))


def _join_to_absolute(dest_path, rel_path):
    return f"/{rel_path}" if dest_path == '/' \
        else f"{dest_path}/{rel_path}"


def _get_normalized_fs_protocol_and_path(uri):
    """
    Take the fsspec path (<proto>://<path>) and return the
    FS object, protocol, and path, removing any trailing slash
    on the path (unless the path indicates the root dir)
    """
    fs, path = _get_fs_and_path(uri)
    # normalize trailing '/' by just removing them unless the path
    # is exactly just '/'
    if path != '/':
        path = path.rstrip('/')
    return fs, fs.protocol, path


def _get_last_modified(protocol: str, info: dict) -> float:
    if protocol == 'xet':
        mod_time = info['last_modified']  # str
        mod_time = datetime.strptime(mod_time, XET_MTIME_FORMAT).timestamp()
    elif protocol == 's3':
        mod_time = info['LastModified']  # datetime
        mod_time = mod_time.timestamp()
    elif protocol == 'file':
        mod_time = info['mtime']  # float
    else:
        print(f"WARN: protocol: {protocol} doesn't have a modification time, only comparing size")
        mod_time = None

    return mod_time


def _should_sync(src_proto, src_info, dest_proto, dest_info):
    if src_info['size'] != dest_info['size']:
        return True

    src_mtime = _get_last_modified(src_proto, src_info)
    dest_mtime = _get_last_modified(dest_proto, dest_info)
    return src_mtime is not None and dest_mtime is not None \
        and src_mtime > dest_mtime

