import subprocess
import threading
import typing

import pyxet
import fsspec
import sys
from concurrent.futures import ThreadPoolExecutor
import os

from .config import CHUNK_SIZE, MAX_CONCURRENT_COPIES
from .url_parsing import parse_url
from .rpyxet import rpyxet
from .file_system import XetFS

XET = 'xet'


def _ltrim_match(s, match):
    """
    Trims the string 'match' from the left of the string 's'
    raising an error if the match does not exist.
    Ex:
    ```
       ltrim_match("a/b/c.txt", "a/b") => "/c.txt"
    ```
    Used to compute relative paths.
    """
    if len(s) < len(match):
        raise (ValueError(f"Path {s} not in directory {match}"))
    if s[:len(match)] != match:
        raise (ValueError(f"Path {s} not in directory {match}"))
    return s[len(match):]


def _get_fs_and_path(uri):
    if uri.find('://') == -1:
        fs = fsspec.filesystem("file")
        uri = os.path.abspath(uri)
        return fs, uri
    else:
        split = uri.split("://")
        if len(split) != 2:
            print(f"Invalid URL: {uri}", file=sys.stderr)
        if split[0] == XET:
            fs = pyxet.XetFS()
        else:
            fs = fsspec.filesystem(split[0])
            # this is *really* annoying But the s3fs protocol has
            # protocol as a list ['s3','s3a']
            if isinstance(fs.protocol, list):
                fs.protocol = split[0]
        return fs, split[1]


def _single_file_copy(src_fs, src_path, dest_fs, dest_path,
                      buffer_size=CHUNK_SIZE, size_hint=None,
                      max_concurrent_copies=MAX_CONCURRENT_COPIES):
    if dest_path.split('/')[-1] == '.gitattributes':
        print("Skipping .gitattributes as that is required for Xet Magic")
        return
    print(f"Copying {src_path} to {dest_path}...")

    if src_fs.protocol == XET and dest_fs.protocol == XET:
        dest_fs.cp_file(src_path, dest_path)
        return
    with max_concurrent_copies:
        try:
            if dest_fs.protocol == "xet":
                if size_hint is None:
                    size_hint = src_fs.info(src_path).get('size', None)

                # Heuristic for now -- if the size of the source is larger than 50MB,
                # then make sure we have any shards for the destination that work.
                if size_hint is not None and size_hint >= 50000000:
                    dest_fs.add_deduplication_hints(dest_path)

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
    if srcproto == XET:
        src_fs.branch_info(src_path)

    if destproto == XET:
        # check dest branch exists
        # exists before we try to do any copying
        # An exception is that if this operation would create a branch
        if srcproto == XET:
            src_parse = parse_url(src_path, src_fs.domain)
            dest_parse = parse_url(dest_path, dest_fs.domain)
            if src_parse.path == '' and dest_parse.path == '':
                # this is a branch to branch copy
                return True

        dest_fs.branch_info(dest_path)


def _isdir(fs, path):
    if fs.protocol == XET:
        return fs.isdir_or_branch(path)
    else:
        return fs.isdir(path)


def _copy(source: str, destination: str, recursive: bool = True,
          _src_fs: fsspec.spec.AbstractFileSystem = None,
          _dest_fs: fsspec.spec.AbstractFileSystem = None,
          max_concurrent_copies: threading.Semaphore = MAX_CONCURRENT_COPIES):
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
        src_root_dir = '/'.join(src_path.split('/')[:-1])
        if '*' in src_root_dir:
            raise ValueError(f"Invalid glob {source}. Wildcards can only appear in the last position")
        # The source path contains a wildcard
        with ThreadPoolExecutor() as executor:
            futures = []
            for path, info in src_fs.glob(src_path, detail=True).items():
                # Copy each matching file
                if info['type'] == 'directory' and not recursive:
                    continue
                relpath = _ltrim_match(path, src_root_dir).lstrip('/')
                if dest_path == '/':
                    dest_for_this_path = f"/{relpath}"
                else:
                    dest_for_this_path = f"{dest_path}/{relpath}"
                dest_dir = '/'.join(dest_for_this_path.split('/')[:-1])
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
        if srcproto == XET and destproto == XET:
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
                relpath = _ltrim_match(path, src_path).lstrip('/')
                if dest_path == '/':
                    dest_for_this_path = f"/{relpath}"
                else:
                    dest_for_this_path = f"{dest_path}/{relpath}"
                dest_dir = '/'.join(dest_for_this_path.split('/')[:-1])
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

    _single_file_copy(src_fs, src_path, dest_fs, dest_path, max_concurrent_copies=max_concurrent_copies)


def _mv(source: str, target: str, recursive: bool, message: str):
    if not message:
        message = f"move {source} to {target}" if not recursive else f"move {source} to {target} recursively"
    src_fs, src_path = _get_fs_and_path(source)
    dest_fs, dest_path = _get_fs_and_path(target)
    if src_fs.protocol != dest_fs.protocol:
        print(
            "Unable to move between different protocols {src_fs.protocol}, {dest_fs.protocol}\nYou may want to copy instead",
            file=sys.stderr)
    destproto_is_xet = dest_fs.protocol == XET
    try:
        if destproto_is_xet:
            dest_fs.start_transaction(message)
        dest_fs.mv(src_path, dest_path)
        if destproto_is_xet:
            dest_fs.end_transaction()
    except Exception as e:
        print(f"{e}")
        return


def _rm(paths=typing.List[str], message=str):
    if not message:
        message = f"delete {paths}"
    fs, _ = _get_fs_and_path(paths[0])
    try:
        destproto_is_xet = fs.protocol == XET
        if destproto_is_xet:
            for path in paths:
                parsed_path = parse_url(path, fs.domain)
                if len(parsed_path.path) == 0 and len(parsed_path.branch) > 0:
                    print(
                        "Cannot delete branches with 'rm' as this is a non-reversible operation and history will not be preserved. Use 'xet branch del'",
                        file=sys.stderr)
                    return
            fs.start_transaction(message)
        for path in paths:
            fs.rm(path)
        if destproto_is_xet:
            fs.end_transaction()
    except Exception as e:
        print(f"{e}")
        return


def _info(uri: str):
    fs, path = _get_fs_and_path(uri)
    return fs.info(path)


def _duplicate(source: str = None,
               dest: str = None,
               private: bool = False,
               public: bool = False,
               verbose: bool = False):
    fs = XetFS()
    if dest is None:
        repo_name = source.rstrip('/').split('/')[-1]
        dest = "xet://" + fs.get_username() + "/" + repo_name
        if verbose:
            print(f"Duplicating to {dest}")
    else:
        repo_name = source.rstrip('/').split('/')[-1]
    fs.duplicate_repo(source, dest)
    try:
        if private:
            if verbose:
                print(f"Duplicate Success. Changing permissions...")
            fs.set_repo_attr(dest, "private", True)
            if verbose:
                print(f"Repo permissions set successfully")
        if public:
            if verbose:
                print(f"Duplicate Success. Changing permissions...")
            fs.set_repo_attr(dest, "public", False)
            if verbose:
                print(f"Repo permissions set successfully")
    except Exception as e:
        username = fs.get_username()
        if verbose:
            print(f"An error has occurred setting repository permissions: {e}")
            print("Permission changes may not have been made. Please change it manually at:")
            print(f"  {fs.domain}/{username}/{repo_name}/settings")


def _root_copy(source, destination, message, recursive=False, max_concurrent_copies=MAX_CONCURRENT_COPIES):
    if not message:
        message = f"copy {source} to {destination}" if not recursive else f"copy {source} to {destination} recursively"
    dest_fs, dest_path = _get_fs_and_path(destination)
    destproto_is_xet = dest_fs.protocol == XET
    dest_isdir = _isdir(dest_fs, dest_path)

    # Our target is an existing directory and src is not a wildcard copy
    # i.e. we are getting cp src/some/path to dest/some/where
    # but dest/some/where exists as a directory
    # So we will need to make the dest dest/some/where/path
    if dest_isdir and '*' not in source:
        # split up the final component from source path and add it
        # to the destination
        final_source_component = source.split('/')[-1]
        if not destination.endswith('/'):
            destination += '/'
        destination += final_source_component

    if destproto_is_xet:
        dest_fs.start_transaction(message)
    _copy(source, destination, recursive, max_concurrent_copies=max_concurrent_copies)
    if destproto_is_xet:
        dest_fs.end_transaction()


def _list(path: str, detail: bool = True):
    fs, path = _get_fs_and_path(path)
    return fs.ls(path, detail=detail)


def configure_login(email: str, user: str, password: str, host: str = "xethub.com", force: bool = False,
                    no_overwrite: bool = False):
    """
    Configures the login information. Stores the config in ~/.xetconfig

    Parameters
    ----------
    email [str]: email address associated with account
    user [str]: user name
    password [str]: password
    host [str]: host to authenticate against (default: xethub.com)
    force [bool]: do not perform authentication check and force write to config
    no_overwrite [bool]: Do not overwrite if existing auth information is found

    Returns
    -------

    """
    return rpyxet.configure_login(host, user, email, password, force, no_overwrite)


def _mount(source: str, path: str, prefetch: int = 2):
    """
    Mounts a repository on a local path

    Parameters
    ----------
    source [str]: Repository and branch of the form xet://user/repo/branch"
    path [str]: Path to mount to. (or a drive letter on windows)
    prefetch [int]: Prefetch blocks in multiple of 16MB. Default=2

    Returns
    -------

    """
    fs = XetFS()
    source = parse_url(source, fs.domain)
    if source.path != '':
        raise ValueError("Cannot have a path when mounting. Expecting only xet://user/repo/branch")
    if source.branch == '':
        raise ValueError("Branch or revision must be specified")
    if os.name == 'nt':
        # path must be a drive letter (X, or X: or X:\\)
        letter = path[0]
        if path != letter and path != letter + ':' and path != letter + ':\\':
            raise ValueError("Path must be a drive letter of the form X:")
        path = letter
    rpyxet.perform_mount(sys.executable, source.remote, path, source.branch, prefetch)


def _perform_mount_curdir(path, reference, signal, autostop, prefetch, ip, writable):
    return rpyxet._perform_mount_curdir(path=path,
                                        reference=reference,
                                        signal=signal,
                                        autostop=autostop,
                                        prefetch=prefetch,
                                        ip=ip,
                                        writable=writable)


def make_branch(repo: str,
                src_branch: str,
                dest_branch: str):
    fs, remote = _get_fs_and_path(repo)
    assert (fs.protocol == XET)
    assert ('/' not in dest_branch)
    fs.make_branch(remote, src_branch, dest_branch)


def list_branches(repo: str, raw: bool = False):
    fs, path = _get_fs_and_path(repo)
    assert (fs.protocol == XET)
    return fs.list_branches(repo, raw)


def delete_branch(repo: str, branch: str):
    fs, path = _get_fs_and_path(repo)
    assert (fs.protocol == XET)
    return fs.delete_branch(repo, branch)


def get_branch_info(repo: str, branch: str):
    fs, path = _get_fs_and_path(repo)
    assert (fs.protocol == XET)
    return fs.find_ref(repo, branch)


def make_repo(name: str, private: bool = False, public: bool = False):
    if private == public:
        raise ValueError("One of --private or --public must be set")
    fs = XetFS()
    ret = fs.make_repo(name)
    if private:
        fs.set_repo_attr(name, "private", True)
    return ret


def fork_repo(source: str, dest: str = None) -> dict:
    """
            Forks a copy of a repository from xet://[user]/[repo] to your own account.
            Defaults to original repository private/public settings.
            If dest is not provided, xet://[yourusername]/[repo] is used.
            Use `xet duplicate` if you want a detached private fork.
            """
    fs = XetFS()
    if dest is None:
        repo_name = source.rstrip('/').split('/')[-1]
        dest = "xet://" + fs.get_username() + "/" + repo_name
    fs.fork_repo(source, dest)


def list_repos(raw: bool = False) -> typing.List[typing.Union[dict, str]]:
    """
    Lists all repositories
    Parameters
    ----------
    raw: bool = False: If True, returns a list of dictionaries with the following keys:

    Returns
    -------

    """
    fs = XetFS()
    return fs.list_repos(raw)


def rename_repo(source: str, dest: str):
    """
    Renames a repository
    Parameters
    ----------
    source [str]: origin repo to rename from (of the form xet://user/repo)
    dest [str]: repo to rename to (xet://user/repo)

    Returns
    -------

    """
    fs = XetFS()
    return fs.rename_repo(source, dest)


def _validate_git_xet():
    """
    Validates that git-xet is installed
    Returns True if git-xet is installed, False otherwise
    -------
    """
    res = subprocess.run(["git-xet", "-V"], capture_output=True)
    if res.returncode != 0:
        print("git-xet not found. Please install git-xet from https://xethub.com/explore/install")
        return False
    return True


def _clone(source: str, *args):
    """

    Parameters
    ----------
    source [str]: Repository and branch of the form xet://user/repo""
    args [list]: Arguments to be passed to git-xet clone

    Returns
    -------
    """

    fs = XetFS()
    source = parse_url(source, fs.domain)
    commands = ["git-xet", "clone"] + [source.remote] + list(args)
    strcommand = ' '.join(commands)
    print(f"Running '{strcommand}'")
    subprocess.run(strcommand, shell=True)


def clone(source: str, *args):
    if _validate_git_xet() is False:
        raise ValueError("git-xet not found. Please install git-xet from https://xethub.com/explore/install")
    _clone(source, *args)
