import os
import posixpath
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import fsspec

from . import XetFS, XetFSOpenFlags
from .url_parsing import parse_url

MAX_CONCURRENT_COPIES = threading.Semaphore(32)
CHUNK_SIZE = 16 * 1024 * 1024


def _should_load_aws_credentials():
    """
    Determines if AWS credentials should be loaded for s3 API by checking if credentials are available
    :return: boolean, True if credentials are available, False
    """
    try:
        import boto3
        import botocore
    except:
        print("boto3 and botocore required for AWS S3 support")
        print("Please install them with 'pip install boto3 botocore'")
        sys.exit(1)
    client = boto3.client("sts")
    try:
        client.get_caller_identity()
    except botocore.exceptions.NoCredentialsError:
        return False
    return True


def _get_fs_and_path(uri):
    if uri.find('://') == -1:
        fs = fsspec.filesystem("file")
        uri = os.path.abspath(uri)
        return fs, uri
    split = uri.split("://")
    if len(split) != 2:
        print(f"Invalid URL: {uri}", file=sys.stderr)
    if split[0] == 'xet':
        fs = XetFS()
    elif split[0] == 's3':
        load_aws_creds = _should_load_aws_credentials()
        fs = fsspec.filesystem('s3', anon=not load_aws_creds)
        # this is *really* annoying But the s3fs protocol has
        # protocol as a list ['s3','s3a']
        fs.protocol = 's3'
    else:
        fs = fsspec.filesystem(split[0])
    return fs, split[1]


def _single_file_copy(src_fs, src_path, dest_fs, dest_path,
                      buffer_size=CHUNK_SIZE, size_hint=None):
    if dest_path.split('/')[-1] == '.gitattributes':
        print("Skipping .gitattributes as that is required for Xet Magic")
        return
    print(f"Copying {src_path} to {dest_path}...")

    if src_fs.protocol == 'xet' and dest_fs.protocol == 'xet':
        dest_fs.cp_file(src_path, dest_path)
        return
    with MAX_CONCURRENT_COPIES:
        try:
            if dest_fs.protocol == "xet":
                if size_hint is None:
                    size_hint = src_fs.info(src_path).get('size', None)

                # Heuristic for now -- if the size of the source is larger than 50MB,
                # then make sure we have any shards for the destination that work.
                if size_hint is not None and size_hint >= 50000000:
                    dest_fs.add_deduplication_hints(dest_path)

            # Fasttrack for downloading a file to local
            if src_fs.protocol == "xet" and dest_fs.protocol == "file":
                with src_fs.open(src_path, "rb", {"flags": XetFSOpenFlags.FILE_FLAG_NO_BUFFERING}) as source_file:
                    source_file.get(dest_path)
            else:
                with src_fs.open(src_path, "rb") as source_file:
                    with dest_fs.open(dest_path, "wb", auto_mkdir=True) as dest_file:
                        # Buffered copy in chunks
                        while True:
                            chunk = source_file.read(buffer_size)
                            if not chunk:
                                break
                            dest_file.write(chunk)
        except Exception as e:
            proto = src_fs.protocol
            print(f"Failed to copy {proto}://{src_path}: {e}")


def _validate_xet_copy(src_fs, src_path, dest_fs, dest_path):
    """
    Performs some basic early validation of a xet to avoid issues later.
    Does not catch all failure conditions, but catches some early enough to
    avoid doing a lot of unnecessary work, then fail.

    Raises an exception on failure, returns True on success
    """
    srcproto = src_fs.protocol
    destproto = dest_fs.protocol
    # if src is a xet, there must be a branch to copy from
    if srcproto == 'xet':
        src_fs.branch_info(src_path)

    if destproto == 'xet':
        # check dest branch exists before we try to do any copying
        # An exception is that if this operation would create a branch
        if srcproto == 'xet':
            src_parse = parse_url(src_path, src_fs.domain)
            dest_parse = parse_url(dest_path, dest_fs.domain)
            if src_parse.path == '' and dest_parse.path == '':
                # this is a branch to branch copy
                return True

        dest_fs.branch_info(dest_path)


def _isdir(fs, path):
    if fs.protocol == 'xet':
        return fs.isdir_or_branch(path)
    else:
        return fs.isdir(path)


def _rel_path(s, start):
    """
    Get the relative path of 's' from 'start'
    Ex:
    ```
       _rel_path("a/b/c.txt", "a/b") => "c.txt"
    ```
    """
    return os.path.relpath(s, start)


# split path into dirname and basename
def _path_split(fs, path):
    if fs.protocol == 'file':
        return os.path.split(path)
    else:
        return path.rsplit('/', 1)


def _path_join(fs, path, *paths):
    if fs.protocol == 'file':
        return os.path.join(path, *paths)
    else:
        return '/'.join([path] + list(map(lambda p: p.strip('/'), paths)))


def _path_dirname(fs, path):
    if fs.protocol == 'file':
        return os.path.dirname(path)
    else:
        return '/'.join(path.split('/')[:-1])


def _copy(source, destination, recursive=True, _src_fs=None, _dest_fs=None):
    src_fs, src_path = _get_fs_and_path(source)
    dest_fs, dest_path = _get_fs_and_path(destination)
    if _src_fs is not None:
        src_fs = _src_fs
    if _dest_fs is not None:
        dest_fs = _dest_fs
    srcproto = src_fs.protocol
    destproto = dest_fs.protocol

    _validate_xet_copy(src_fs, src_path, dest_fs, dest_path)

    # normalize trailing '/' by just removing them unless the path
    # is exactly just '/'
    if src_path != '/':
        src_path = src_path.rstrip('/')
    if dest_path != '/':
        dest_path = dest_path.rstrip('/')
    src_isdir = _isdir(src_fs, src_path)

    # Handling wildcard cases
    if '*' in src_path:
        # validate
        # we only accept globs of the for blah/blah/blah/[glob]
        # i.e. the glob is only in the last component
        # src_root_dir should be blah/blah/blah here
        src_root_dir, _ = _path_split(src_fs, src_path)
        if '*' in src_root_dir:
            raise ValueError(f"Invalid glob {source}. Wildcards can only appear in the last position")
        # The source path contains a wildcard
        with ThreadPoolExecutor() as executor:
            futures = []
            for path, info in src_fs.glob(src_path, detail=True).items():
                # Copy each matching file
                if info['type'] == 'directory' and not recursive:
                    continue
                relpath = _rel_path(path, src_root_dir)
                if src_fs.protocol == 'file' and os.sep != posixpath.sep:
                    relpath = relpath.replace(os.sep, posixpath.sep)
                dest_for_this_path = _path_join(dest_fs, dest_path, relpath)
                dest_dir = _path_dirname(dest_fs, dest_for_this_path)
                dest_fs.makedirs(dest_dir, exist_ok=True)

                if info['type'] == 'directory':
                    futures.append(
                        executor.submit(
                            _copy,
                            f"{src_fs.protocol}://{path}",
                            f"{dest_fs.protocol}://{dest_for_this_path}",
                            recursive=True,
                            _src_fs=src_fs,
                            _dest_fs=dest_fs,
                        )
                    )
                else:
                    futures.append(
                        executor.submit(
                            _single_file_copy,
                            src_fs,
                            f"{path}",
                            dest_fs,
                            dest_for_this_path,
                            size_hint=info.get('size', None)
                        ))

            for future in futures:
                future.result()
        return

    # Handling directories
    if src_isdir:
        # Recursively copy
        # xet cp_file can cp directories
        if srcproto == 'xet' and destproto == 'xet':
            print(f"Copying {src_path} to {dest_path}...")
            dest_fs.cp_file(src_path, dest_path)
            return
        with ThreadPoolExecutor() as executor:
            futures = []
            for path, info in src_fs.find(src_path, detail=True).items():
                if info['type'] == 'directory' and not recursive:
                    continue
                # Note that path is a full path
                # we need to relativize to make the destination path
                relpath = _rel_path(path, src_path)
                if src_fs.protocol == 'file' and os.sep != posixpath.sep:
                    relpath = relpath.replace(os.sep, posixpath.sep)
                dest_for_this_path = _path_join(dest_fs, dest_path, relpath)
                dest_dir = _path_dirname(dest_fs, dest_for_this_path)
                dest_fs.makedirs(dest_dir, exist_ok=True)

                # Submitting copy jobs to thread pool
                futures.append(
                    executor.submit(
                        _single_file_copy,
                        src_fs,
                        f"{path}",
                        dest_fs,
                        dest_for_this_path,
                        size_hint=info.get('size', None)
                    ))
            # Waiting for all copy jobs to complete
            for future in futures:
                future.result()
        return

    _single_file_copy(src_fs, src_path, dest_fs, dest_path)


def _root_copy(source, destination, message, recursive=False, do_not_commit=False):
    dest_fs, dest_path = _get_fs_and_path(destination)
    destproto_is_xet = dest_fs.protocol == 'xet'
    dest_isdir = _isdir(dest_fs, dest_path)

    # Our target is an existing directory and src is not a wildcard copy
    # i.e. we are getting cp src/some/path to dest/some/where
    # but dest/some/where exists as a directory
    # So we will need to make the dest dest/some/where/path
    if dest_isdir and '*' not in source:
        # split up the final component from source path and add it
        # to the destination
        src_fs, _ = _get_fs_and_path(source)
        _, final_source_component = _path_split(src_fs, source)
        if not destination.endswith('/'):
            destination += '/'
        destination += final_source_component

    if destproto_is_xet:
        tr = dest_fs.start_transaction(message)
        if do_not_commit:
            tr._set_do_not_commit()
    _copy(source, destination, recursive)
    if destproto_is_xet:
        dest_fs.end_transaction()
