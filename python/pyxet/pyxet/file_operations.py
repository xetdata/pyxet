import os
import posixpath
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from collections import namedtuple

import fsspec

from . import XetFS, XetFSOpenFlags
from .url_parsing import parse_url
from .util import _path_split, _path_normalize, _path_join, \
  _path_dirname, _isdir, _get_fs_and_path, _rel_path

MAX_CONCURRENT_COPIES = threading.Semaphore(32)
CHUNK_SIZE = 16 * 1024 * 1024


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
        # check dest branch exists
        # exists before we try to do any copying
        # An exception is that if this operation would create a branch
        if srcproto == 'xet':
            src_parse = parse_url(src_path, src_fs.domain)
            dest_parse = parse_url(dest_path, dest_fs.domain)
            if src_parse.path == '' and dest_parse.path == '':
                # this is a branch to branch copy
                return True

        dest_fs.branch_info(dest_path)


class CopyUnit:
    __slots__ = ['src_path', 'dest_path', 'dest_dir', 'size']

    def __init__(self, src_path, dest_path, dest_dir, size = None):
        self.src_path = src_path
        self.dest_path = dest_path
        self.dest_dir = dest_dir
        self.size = size

    def __repr__(self):
        return f"[CopyUnit: {self.src_path} to {self.dest_path} (dir = {self.dest_dir}), size = {self.size}]"

def _single_file_copy_impl(cp_action, src_fs, dest_fs, buffer_size=CHUNK_SIZE):

    src_path = cp_action.src_path
    dest_path = cp_action.dest_path

    print(f"Copying {src_path} to {dest_path}")

    if src_fs.protocol == 'xet' and dest_fs.protocol == 'xet':
        dest_fs.cp_file(src_path, dest_path)
        return
    
    dest_is_xet = dest_fs.protocol == "xet"

    with MAX_CONCURRENT_COPIES:
        try:
            if cp_action.dest_dir is not None and not dest_is_xet: 
                dest_fs.makedirs(cp_action.dest_dir, exist_ok = True)

            if dest_is_xet:
                size_hint = cp_action.size

                if size_hint is None:
                    size_hint = src_fs.info(src_path).get('size', None)

                # Heuristic for now -- if the size of the source is larger than 50MB,
                # then make sure we have any shards for the destination that work.
                if size_hint is not None and size_hint >= 50000000:
                    dest_fs.add_deduplication_hints(dest_path)

            # Fasttrack for downloading a file to local
            if src_fs.protocol == "xet" and dest_fs.protocol == "file":
                with src_fs.open(src_path, "rb", flags=XetFSOpenFlags.FILE_FLAG_NO_BUFFERING) as source_file:
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
            raise
        

        
def single_file_copy(src_fs, src_path, dest_fs, dest_path, size_hint = None):
    """
    Immediately performs a copy of a single file.

    Note this requires the destination to be inside a transaction.
    """
    
    # Our target is an existing directory i.e. we are getting cp src/some/path to dest/some/where
    # but dest/some/where exists as a directory
    # So we will need to make the dest dest/some/where/path
    if _isdir(dest_fs, dest_path): 
        # Split up the final component from source path and add it
        # to the destination.
        # We get final component from 'source' instead of the 
        # normalized 'src_path' because if 'source' ends with 
        # '/' or '\', the desired behavior is to copy what's 
        # under that directory, and to skip 'source' itself.
        final_source_component = _path_split(src_fs, src_path)
        file_dest_path = _path_join(dest_fs, dest_path, final_source_component)
        cp_unit = CopyUnit(src_path=src_path, dest_path=file_dest_path, dest_dir = None, size = size_hint)
    else:
        dest_dir = _path_split(dest_fs, dest_path)
        if _isdir(dest_fs, dest_dir):
          dest_dir = None # No need to create this

        cp_unit = CopyUnit(src_path=src_path, dest_path=dest_path, dest_dir = dest_dir, size = size_hint)
                           
    _single_file_copy_impl(cp_unit, src_fs, dest_fs)


def _build_cp_action_list_impl(src_fs, src_path, dest_fs, dest_path, recursive):
    
    dest_is_xet = dest_fs.protocol == "xet"
    # If both the source and the end is a xet, then this can be done 
    dirs_directly_copyable = dest_is_xet and src_fs.protocol == "xet"

    dest_has_trailing_slash = dest_path.endswith("/") 
    dest_path = dest_path.rstrip("/")

    # Handling wildcard cases
    if '*' in src_path:

        # validate
        # we only accept globs of the for blah/blah/blah/[glob]
        # i.e. the glob is only in the last component
        # src_root_dir should be blah/blah/blah here
        src_root_dir, end_component = _path_split(src_fs, src_path)

        if '*' in src_root_dir:
            raise ValueError(
                f"Invalid glob {src_path}. Wildcards can only appear in the last position")

        src_path = src_root_dir 
        glob_pattern = end_component if end_component != "*" else None

        # Ensure we have the right behavior here below.
        src_path_trailing_slash = True
        dest_has_trailing_slash = True

        dest_dir=dest_path
        dest_path=None # In this case, the path information will be taken from the source file name.
        src_isdir=True

    else:
        glob_pattern = None

        src_path_trailing_slash = src_path.endswith("/")
        
        if src_path_trailing_slash:
            src_path = src_path.rstrip("/")
            src_isdir = True
            if not _isdir(src_fs, src_path): 
                raise ValueError(f"Source path {src_path} not an existing directory.")
        else:
            src_isdir = _isdir(src_fs, src_path)

        # Handling directories
        if src_isdir:
            if not recursive:
                raise ValueError(
                    "Specify recursive flag '-r' to copy directories.")

        # Figure out what the destination is like, etc. 
        try:
            info = dest_fs.info(dest_path)

            if info["type"] in ["directory", "branch"]:

                if src_isdir:
                    _, end_component = _path_split(src_fs, src_path)
                    dest_dir = _path_join(dest_fs, dest_path, end_component)

                    dest_path = None
                else:
                    _, end_component = _path_split(src_fs, src_path)
                    dest_path = _path_join(dest_fs, dest_path, end_component)
                    dest_dir = _path_dirname(dest_fs, dest_path)

            else:
                if src_isdir:
                    # Dest exists, but it's a regular file.
                    raise ValueError(
                        "Copy: source is a directory, but destination is not.")
                else:
                    dest_dir = _path_dirname(dest_fs, dest_path)

        except FileNotFoundError:
            # When the destination doesn't exist
            if src_isdir:
                dest_dir = dest_path
                dest_path = None
            else:
                if dest_has_trailing_slash:
                    # xet cp dir/subdir/file dest/d1/  -> goes into dest/d1/file
                    dest_dir = dest_path
                    _, end_component = _path_split(src_fs, src_path)
                    dest_path = _path_join(dest_fs, dest_dir, end_component)
                else:
                    # xet cp dir/subdir/file dest/f1  -> goes into dest/f1
                    dest_dir = _path_dirname(dest_fs, dest_path)


    # Now build up the list based on these parameters
    if src_isdir:

        # Build the recursive case
        if recursive:
            # Handle the xet -> xet case
            if glob_pattern is None and dirs_directly_copyable:
                return [CopyUnit(src_path=src_path, dest_path=dest_dir, dest_dir=None, size=None)]
                                 
            src_listing = src_fs.find(src_path, detail=True).items()

        else:
            pattern = _path_join(src_fs, src_path, glob_pattern if glob_pattern is not None else '*')
            src_listing = src_fs.glob(pattern, detail=True).items()

        cp_files = []

        for src_p, info in src_listing:
            if info['type'] == 'directory':
                # Find is already recursive, and glob is not used in the recursive case
                continue

            rel_path = _rel_path(src_p, src_path)

            if glob_pattern is not None:
                if not fnmatch(rel_path, glob_pattern):
                    continue

            dest_path = _path_join(dest_fs, dest_dir, rel_path)
            base_dir = _path_dirname(dest_fs, dest_path)
            
            cp_files.append(CopyUnit(src_path=src_p, dest_path = dest_path, dest_dir = base_dir, size = info.get('size', 0)))

        return cp_files
    else:
        src_size = src_fs.info(src_path).get('size', 0)

        if _isdir(dest_fs, dest_path):
            _, file_name = _path_split(src_fs, src_path)
            return [CopyUnit(src_path=src_path, dest_path=os.path.join(dest_path, file_name), dest_dir=dest_path, size=src_size)]
        else:
            dest_dir=_path_dirname(dest_fs, dest_path)
            return [CopyUnit(src_path=src_path, dest_path=dest_path, dest_dir=dest_dir, size=src_size)]




def build_cp_action_list(source, destination, recursive=False):
    """
    Builds a list of actions that need to be performed to do a copy operation.
    """

    src_fs, src_path = _get_fs_and_path(source, strip_trailing_slash=False)
    dest_fs, dest_path = _get_fs_and_path(destination, strip_trailing_slash=False)

    return _build_cp_action_list_impl(
        src_fs, src_path, dest_fs, dest_path, recursive)
    

def perform_copy(source, destination, message, recursive=False):
    """
    Performs a copy operation. 
    """

    src_fs, src_path = _get_fs_and_path(source, strip_trailing_slash=False)
    dest_fs, dest_path = _get_fs_and_path(destination, strip_trailing_slash=False)
    
    destproto_is_xet = dest_fs.protocol == "xet"
    
    _validate_xet_copy(src_fs, src_path, dest_fs, dest_path)
    
    if destproto_is_xet:
        dest_fs.start_transaction(message)
    
    try:

        # Get the list of everything to copy.
        cp_list = _build_cp_action_list_impl(
            src_fs, src_path, dest_fs, dest_path, recursive)

        # Now, go through and do all the actual copying.
        futures = []
        opt_future = None
        with ThreadPoolExecutor() as executor:
            for cp_action in cp_list:
                futures.append(executor.submit(_single_file_copy_impl, cp_action,
                            src_fs, dest_fs))

        for future in futures:
            future.result()

        if opt_future is not None:
            # Head scratch -- will this actually cancel it when it's running in rust?
            opt_future.cancel()

    finally:
        if destproto_is_xet:
            dest_fs.end_transaction()
