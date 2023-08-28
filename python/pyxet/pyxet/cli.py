import os
import subprocess
import sys
import threading
import typing
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
from datetime import datetime

import boto3
import botocore
import fsspec
import typer
from tabulate import tabulate
from typing_extensions import Annotated

import pyxet
from .file_system import XetFS
from .rpyxet import rpyxet
from .url_parsing import parse_url
from .version import __version__

cli = typer.Typer(add_completion=True, short_help="a pyxet command line interface", no_args_is_help=True)
repo = typer.Typer(add_completion=False, short_help="sub-commands to manage repositories")
branch = typer.Typer(add_completion=False, short_help="sub-commands to manage branches")

cli.add_typer(repo, name="repo")
cli.add_typer(branch, name="branch")

MAX_CONCURRENT_COPIES = threading.Semaphore(32)
CHUNK_SIZE = 16 * 1024 * 1024


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


def _should_load_aws_credentials():
    """
    Determines if AWS credentials should be loaded for s3 API by checking if credentials are available
    :return: boolean, True if credentials are available, False
    """
    client = boto3.client("sts")
    try:
        client.get_caller_identity()
    except botocore.exceptions.NoCredentialsError:
        return False
    return True


def _get_fs_and_path(uri) -> tuple[fsspec.spec.AbstractFileSystem, str]:
    if uri.find('://') == -1:
        fs = fsspec.filesystem("file")
        uri = os.path.abspath(uri)
        return fs, uri
    split = uri.split("://")
    if len(split) != 2:
        print(f"Invalid URL: {uri}", file=sys.stderr)
    if split[0] == 'xet':
        fs = pyxet.XetFS()
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


def _validate_xet_sync(source, destination):
    """
    Performs early validation for the source and destination paths of
    a xet sync. Doesn't catch all failure conditions, but catches many
    of the easy validations.

    Raises exceptions on failure
    """
    src_fs, src_path = _get_fs_and_path(source)
    src_protocol = src_fs.protocol
    dest_fs, dest_path = _get_fs_and_path(destination)
    dest_protocol = dest_fs.protocol

    if dest_protocol != 'xet':
        raise ValueError(f"Unsupported destination protocol: {dest_protocol}, only xet:// targets are supported")
    if src_protocol == 'xet':
        raise ValueError(f"Unsupported source protocol: {src_protocol}, only non-xet sources are supported")

    # check that the destination specifies an existing branch
    # TODO: we may want to be able to sync remote location to a new branch?
    dest_fs.branch_info(dest_path)

    # source should be a directory
    if not _isdir(src_fs, src_path):
        raise ValueError(f"source: {source} needs to be a directory")

    # wildcards not supported
    if '*' in src_path or '*' in dest_path:
        raise ValueError(f"Wildcards not supported in path")


def _isdir(fs, path):
    if fs.protocol == 'xet':
        return fs.isdir_or_branch(path)
    else:
        return fs.isdir(path)


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

    _single_file_copy(src_fs, src_path, dest_fs, dest_path)


def _root_copy(source, destination, message, recursive=False):
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
        final_source_component = source.split('/')[-1]
        if not destination.endswith('/'):
            destination += '/'
        destination += final_source_component

    if destproto_is_xet:
        dest_fs.start_transaction(message)
    _copy(source, destination, recursive)
    if destproto_is_xet:
        dest_fs.end_transaction()


def _get_last_modified(protocol, info):
    if protocol == 'xet':
        mod_time = info['last_modified']  # str
        mod_time = datetime.strptime(mod_time, "%Y-%m-%dT%H:%M:%S%z").timestamp()
        # mod_time = datetime.fromisoformat(mod_time).timestamp()
    elif protocol == 's3':
        mod_time = info['LastModified']  # datetime
        mod_time = mod_time.timestamp()
    elif protocol == 'file':
        mod_time = info['mtime']  # float
    else:
        print(f"WARN: protocol: {protocol} doesn't have a modification time, only comparing size")
        mod_time = None

    return mod_time


def _should_sync(src_fs, src_info, dest_fs, dest_info):
    if src_info['size'] != dest_info['size']:
        return True

    src_mtime = _get_last_modified(src_fs.protocol, src_info)
    dest_mtime = _get_last_modified(dest_fs.protocol, dest_info)
    return src_mtime is not None and dest_mtime is not None \
        and src_mtime > dest_mtime


def _copy_dir_async(executor, futures, src_fs, src_path, dest_fs, dest_path, dryrun):
    for path, info in src_fs.find(src_path, detail=True).items():
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
        print(f'copy: {src_fs.protocol}://{path} to {dest_fs.protocol}://{dest_for_this_path}')
        if not dryrun:
            futures.append(
                executor.submit(
                    _single_file_copy,
                    src_fs,
                    f"{path}",
                    dest_fs,
                    dest_for_this_path,
                    size_hint=info.get('size', None)
                ))


def _sync(source, destination, message, dryrun):
    print(f"Checking sync {source} -> {destination}")
    _validate_xet_sync(source, destination)
    print(f"Starting sync {source} -> {destination}")

    src_fs, src_path = _get_fs_and_path(source)
    dest_fs, dest_path = _get_fs_and_path(destination)

    # normalize trailing '/' by just removing them unless the path
    # is exactly just '/'
    if src_path != '/':
        src_path = src_path.rstrip('/')
    if dest_path != '/':
        dest_path = dest_path.rstrip('/')

    failed_copies = []

    if not dryrun:
        dest_fs.start_transaction(message)
    with ThreadPoolExecutor() as executor:
        futures = []
        # print(f"listing {src_path}")
        _sync_dir(executor, futures, failed_copies, src_fs, src_path, dest_fs, dest_path, dryrun)

        # Waiting for all copy jobs to complete
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Error: {e}")
                failed_copies.append("")

    if not dryrun:
        dest_fs.end_transaction()
        print(f"Completed sync with: {len(failed_copies)} failed copies")


def _sync_dir(executor, futures, failed_copies, src_fs, src_path, dest_fs, dest_path, dryrun):
    src_proto = src_fs.protocol
    dest_proto = dest_fs.protocol
    for src_info in src_fs.ls(src_path, detail=True):
        # print(f"found: {src_info} from source")
        abs_path = src_info['name']
        rel_path = _ltrim_match(abs_path, src_path).lstrip('/')
        dest_for_this_path = f"/{rel_path}" if dest_path == '/' \
            else f"{dest_path}/{rel_path}"

        # print(f"checking destination: {dest_for_this_path}")
        try:
            dest_info = dest_fs.info(dest_for_this_path)
        except FileNotFoundError as e:
            dest_info = None

        # print(f"found: {dest_info} from destination")
        if dest_info is not None and src_info['type'] != dest_info['type']:
            failed_copies.append(rel_path)
            print(f"Copy failed: {src_path} is a {src_info['type']}, {dest_path} is a {dest_info['type']}")
            continue

        if dest_info is None:
            # copy src to dest
            # dest_dir = '/'.join(dest_for_this_path.split('/')[:-1])
            # dest_fs.makedirs(dest_dir, exist_ok=True)
            if src_info['type'] == 'directory':
                print(f"copy dir: {abs_path} to: {dest_for_this_path}")
                _copy_dir_async(executor, futures, src_fs, abs_path, dest_fs, dest_for_this_path, dryrun)
            else:
                print(f"copy: {src_proto}://{abs_path} to: {dest_proto}://{dest_for_this_path}")
                if not dryrun:
                    futures.append(
                        executor.submit(
                            _single_file_copy,
                            src_fs,
                            f"{abs_path}",
                            dest_fs,
                            dest_for_this_path,
                            size_hint=src_info.get('size', None)
                        ))
        elif src_info['type'] == 'directory':
            # recursively sync src -> dest
            print(f"sync dir: {abs_path} to: {dest_for_this_path}")
            _sync_dir(executor, futures, failed_copies, src_fs, abs_path, dest_fs, dest_for_this_path, dryrun)
        elif _should_sync(src_fs, src_info, dest_fs, dest_info):
            # copy src to dest
            print(f"copy: {src_proto}://{abs_path} to: {dest_proto}://{dest_for_this_path}")
            if not dryrun:
                futures.append(
                    executor.submit(
                        _single_file_copy,
                        src_fs,
                        f"{abs_path}",
                        dest_fs,
                        dest_for_this_path,
                        size_hint=src_info.get('size', None)
                    ))


class PyxetCLI:
    @staticmethod
    @cli.command()
    def login(email: Annotated[str, typer.Option("--email", "-e", help="email address associated with account")],
              user: Annotated[str, typer.Option("--user", "-u", help="user name")],
              password: Annotated[str, typer.Option("--password", "-p", help="password")],
              host: Annotated[str, typer.Option("--host", "-h", help="host to authenticate against")] = "xethub.com",
              force: Annotated[bool, typer.Option("--force", "-f",
                                                  help="do not perform authentication check and force write to config")] = False,
              no_overwrite: Annotated[bool, typer.Option("--no_overwrite",
                                                         help="Do not overwrite if existing auth information is found")] = False):
        """
        Configures the login information. Stores the config in ~/.xetconfig
        """
        rpyxet.configure_login(host, user, email, password, force, no_overwrite)

    @staticmethod
    @cli.command()
    def mount(
            source: Annotated[str, typer.Argument(help="Repository and branch in format xet://[user]/[repo]/[branch]")],
            path: Annotated[str, typer.Argument(help="Path to mount to or a Windows drive letter)")],
            prefetch: Annotated[int, typer.Option(help="Prefetch blocks in multiple of 16MB. Default=32")] = 32):
        """
        Mounts a repository on a local path
        """
        fs = XetFS()
        source = parse_url(source, fs.domain)
        if source.path != '':
            raise ValueError("Cannot have a path when mounting. Expecting xet://[user]/[repo]/[branch]")
        if source.branch == '':
            raise ValueError("Branch or revision must be specified")
        if os.name == 'nt':
            # path must be a drive letter (X, or X: or X:\\)
            letter = path[0]
            if path != letter and path != letter + ':' and path != letter + ':\\':
                raise ValueError("Path must be a Windows drive letter in format X:")
            path = letter
        rpyxet.perform_mount(sys.executable, source.remote, path, source.branch, prefetch)

    @staticmethod
    @cli.command(name="mount-curdir", hidden=True)
    def mount_curdir(path: Annotated[str, typer.Argument(help="path to mount to")],
                     autostop: Annotated[
                         bool, typer.Option('--autostop', help="Automatically terminates on unmount")] = False,
                     reference: Annotated[
                         str, typer.Option('--reference', '-r', help="branch or revision to mount")] = 'HEAD',
                     prefetch: Annotated[int, typer.Option('--prefetch', '-p', help="prefetch aggressiveness")] = 32,
                     ip: Annotated[str, typer.Option('--ip', help="IP used to host the NFS server")] = "127.0.0.1",
                     writable: Annotated[bool, typer.Option('--writable', help="Experimental. Do not use")] = False,
                     signal: Annotated[int, typer.Option('--signal', help="Internal:Sends SIGUSR1 to this pid")] = -1):
        """
        Internal Do not use
        """
        rpyxet.perform_mount_curdir(path=path,
                                    reference=reference,
                                    signal=signal,
                                    autostop=autostop,
                                    prefetch=prefetch,
                                    ip=ip,
                                    writable=writable)

    @staticmethod
    @cli.command()
    def clone(source: Annotated[str, typer.Argument(help="Repository in format xet://[user]/[repo]")],
              args: Annotated[typing.List[str], typer.Argument(help="Arguments to be passed to git-xet clone")] = None):
        """
        Clones a repository on a local path
        """
        res = subprocess.run(["git-xet", "-V"], capture_output=True)
        if res.returncode != 0:
            print("git-xet not found. Please install git-xet from https://xethub.com/explore/install")
            return
        fs = XetFS()
        source = parse_url(source, fs.domain)
        commands = ["git-xet", "clone"] + [source.remote] + args
        strcommand = ' '.join(commands)
        print(f"Running '{strcommand}'")
        subprocess.run(["git-xet", "clone"] + [source.remote] + args)

    @staticmethod
    @cli.command()
    def version():
        """
        Prints the current Xet-cli version
        """
        print(__version__)

    @cli.command()
    def cp(source: Annotated[str, typer.Argument(help="Source file or folder to copy")],
           target: Annotated[str, typer.Argument(help="Target location of the file or folder")],
           recursive: Annotated[
               bool, typer.Option("--recursive", "-r", help="Recursively copy files and folders ")] = False,
           message: Annotated[
               str, typer.Option("--message", "-m", help="A commit message")] = "",
           parallel: Annotated[
               int, typer.Option("--parallel", "-p", help="Maximum amount of parallelism")] = 32):
        """copy files and folders"""
        if not message:
            message = f"copy {source} to {target}" if not recursive else f"copy {source} to {target} recursively"
        MAX_CONCURRENT_COPIES = threading.Semaphore(parallel)
        _root_copy(source, target, message, recursive=recursive)

    @staticmethod
    @cli.command()
    def sync(source: Annotated[str, typer.Argument(help="Source folder to sync")],
             target: Annotated[str, typer.Argument(help="Target location of the folder")],
             message: Annotated[str, typer.Option("--message", "-m", help="A commit message")] = "",
             parallel: Annotated[int, typer.Option("--parallel", "-p", help="Maximum amount of parallelism")] = 32,
             dryrun: Annotated[
                 bool, typer.Option("--dryrun",
                                    help="Displays the operations that would be performed without actually running them")] = False):
        """Copy changed files from source location to destination"""
        if not message:
            message = f"sync {source} to {target}"
        MAX_CONCURRENT_COPIES = threading.Semaphore(parallel)
        _sync(source, target, message, dryrun)

    @staticmethod
    @cli.command()
    def ls(path: Annotated[str, typer.Argument(help="Source file or folder to list")] = "xet://",
           raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """list files and folders"""
        original_path = path
        fs, path = _get_fs_and_path(path)
        try:
            listing = fs.ls(path, detail=True)
            if raw:
                print(listing)
            else:
                if fs.protocol == 'xet':
                    for entry in listing:
                        entry['name'] = 'xet://' + entry['name']
                print(tabulate(listing, headers="keys"))
            return listing
        except Exception as e:
            # this failed to list. retry as a file
            if fs.protocol == 'xet':
                return PyxetCLI.info(original_path, raw)
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def cat(path: Annotated[str, typer.Argument(help="Source file or folder to print")],
            limit: Annotated[int, typer.Option(help="Maximum number of bytes to print")] = 0):
        """Prints a file to stdout"""
        fs, path = _get_fs_and_path(path)
        try:
            file = fs.open(path, 'rb')
            if limit == 0:
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sys.stdout.buffer.write(chunk)
            else:
                chunk = file.read(limit)
                sys.stdout.buffer.write(chunk)
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def rm(paths: Annotated[typing.List[str], typer.Argument(help="File or folder to delete")],
           message: Annotated[
               str, typer.Option("--message", "-m", help="A commit message")] = ""):
        """delete files and folders"""
        if not message:
            message = f"delete {paths}"
        fs, _ = _get_fs_and_path(paths[0])
        try:
            destproto_is_xet = fs.protocol == 'xet'
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

    @staticmethod
    @cli.command()
    def mv(source: Annotated[str, typer.Argument(help="Source file or folder to move")],
           target: Annotated[str, typer.Argument(help="Target location or name to move to")],
           recursive: Annotated[
               bool, typer.Option("--recursive", "-r", help="Recursively copy files and folders ")] = False,
           message: Annotated[
               str, typer.Option("--message", "-m", help="A commit message")] = ""):
        """move files and folders"""
        if not message:
            message = f"move {source} to {target}" if not recursive else f"move {source} to {target} recursively"
        src_fs, src_path = _get_fs_and_path(source)
        dest_fs, dest_path = _get_fs_and_path(target)
        if src_fs.protocol != dest_fs.protocol:
            print(
                "Unable to move between different protocols {src_fs.protocol}, {dest_fs.protocol}\nYou may want to copy instead",
                file=sys.stderr)
        destproto_is_xet = dest_fs.protocol == 'xet'
        try:
            if destproto_is_xet:
                dest_fs.start_transaction(message)
            dest_fs.mv(src_path, dest_path)
            if destproto_is_xet:
                dest_fs.end_transaction()
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def info(uri: Annotated[str, typer.Argument(help="A URI in format xet://[user]/[repo]/[branch]")],
             raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """Provide information about any path"""
        fs, path = _get_fs_and_path(uri)
        try:
            info = fs.info(path)
            if raw:
                print(info)
            else:
                if fs.protocol == 'xet':
                    info['name'] = 'xet://' + info['name']
                print(tabulate([info], headers="keys"))
            return info
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def duplicate(source: Annotated[str, typer.Argument(help="Origin repo to fork from")],
                  dest: Annotated[str, typer.Argument(help="New repository name")] = None,
                  private: Annotated[bool, typer.Option('--private', help="make repository private")] = False,
                  public: Annotated[bool, typer.Option('--public', help="make repository public")] = False,
                  ):
        """
        Duplicates (via a detached fork) a copy of a repository from xet://[user]/[repo] to your own account.
        Defaults to original repository private/public settings. Use --private or --public to adjust the repository permissions. 
        If dest is not provided, xet://[yourusername]/[repo] is used.
        Use `xet fork` if you want a regular fork.
        """

        fs = XetFS()
        if dest is None:
            repo_name = source.rstrip('/').split('/')[-1]
            username = fs.get_username().strip()
            if not bool(username):
                print("Failed to infer a username to duplicate the repo, please provide a full target name")
                return
            dest = "xet://" + username + "/" + repo_name
            print(f"Duplicating to {dest}")
        else:
            repo_name = source.rstrip('/').split('/')[-1]
        fs.duplicate_repo(source, dest)
        try:
            if private:
                print(f"Duplicate successful. Changing permissions...")
                fs.set_repo_attr(dest, "private", True)
                print(f"Repo permissions set successfully")
            if public:
                print(f"Duplicate successful. Changing permissions...")
                fs.set_repo_attr(dest, "public", False)
                print(f"Repo permissions set successfully")
        except Exception as e:
            username = fs.get_username()
            print(f"An error has occurred setting repository permissions: {e}")
            print("Permission changes may not have been made. Please change it manually at:")
            print(f"  {fs.domain}/{username}/{repo_name}/settings")


class BranchCLI:
    @staticmethod
    @branch.command()
    def make(repo: Annotated[str, typer.Argument(help="Repository name in format xet://[user]/[repo]")],
             src_branch: Annotated[str, typer.Argument(help="Source branch to copy")],
             dest_branch: Annotated[str, typer.Argument(help="New branch name")]):
        """
        make a new branch copying another branch.
        Branch names with "/" are not supported.

        Example: Create a new branch from the main branch

            xet branch make xet://user/repo main new_branch
        """
        fs, remote = _get_fs_and_path(repo)
        assert (fs.protocol == 'xet')
        assert ('/' not in dest_branch)
        fs.make_branch(remote, src_branch, dest_branch)

    @staticmethod
    @branch.command()
    def ls(repo: Annotated[str, typer.Argument(help="Repository name in format xet://[user]/[repo]")],
           raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """
        list branches of a repository.
        """
        fs, path = _get_fs_and_path(repo)
        if fs.protocol != 'xet':
            print("Please specify a valid repository name in format xet://[user]/[repo]")
            return
        try:
            listing = fs.list_branches(repo, raw)
            listing = [{'name': "xet://" + path + '/' + n['name'], 'type': 'branch'} for n in listing]
            if raw:
                print(listing)
            else:
                print(tabulate(listing, headers="keys"))
            return listing
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @branch.command()
    def delete(repo: Annotated[str, typer.Argument(help="Repository name in format xet://[user]/[repo]")],
               branch: Annotated[str, typer.Argument(help="Branch to delete")],
               yes: Annotated[bool, typer.Option(help="Type yes to delete")] = False):
        """
        Deletes a branch. Note that this is not an easily reversible operation.
        """
        print("---------------------------------------------------", file=sys.stderr)
        print("                    WARNING", file=sys.stderr)
        print("---------------------------------------------------", file=sys.stderr)
        print("Branch deletion is not a easily reversible operation", file=sys.stderr)
        print("Any data which only exists on a branch will become irreversibly inaccessible", file=sys.stderr)
        print("", file=sys.stderr)
        if yes:
            print("--yes is set. Issuing deletion", file=sys.stderr)
            fs, path = _get_fs_and_path(repo)
            if fs.protocol != 'xet':
                print("Please specify a valid repository name xet://[user]/[repo]")
                return
            return fs.delete_branch(repo, branch)
        else:
            print("Add --yes to delete", file=sys.stderr)

    @staticmethod
    @branch.command()
    def info(repo: Annotated[str, typer.Argument(help="Repository name in format xet://[user]/[repo]")],
             branch: Annotated[str, typer.Argument(help="Branch to query")]):
        """
        Prints information about a branch
        """
        fs, path = _get_fs_and_path(repo)
        if fs.protocol != 'xet':
            print("Please specify a valid repository name in format xet://[user]/[repo]")
            return
        ret = fs.find_ref(repo, branch)
        print(ret)
        return ret


class RepoCLI:
    @staticmethod
    @repo.command()
    def make(name: Annotated[str, typer.Argument(help="Repository name in format xet://[user]/[repo]")],
             private: Annotated[bool, typer.Option('--private', help="Make repository private")] = False,
             public: Annotated[bool, typer.Option('--public', help="Make repository public")] = False,
             ):
        """
        make a new empty repository. Either --private or --public must be set
        """
        if private == public:
            print("Either --private or --public must be set")
            return
        fs = XetFS()
        ret = fs.make_repo(name)
        if private:
            print("Creation successful. Changing permissions...")
            fs.set_repo_attr(name, "private", True)
            print("Repo permissions set successfully")
        print(ret)

    @staticmethod
    @repo.command()
    def fork(source: Annotated[str, typer.Argument(help="Origin repo to fork from")],
             dest: Annotated[str, typer.Argument(help="New repository name")] = None,
             ):
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
            print(f"Forking to {dest}")
        fs.fork_repo(source, dest)

    @staticmethod
    @repo.command()
    def ls(raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """
        list repositories of a user.
        """
        fs = XetFS()
        try:
            repos = fs.list_repos(raw)
            if raw:
                print(repos)
            else:
                print(tabulate(repos, headers="keys"))
            return repos
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @repo.command()
    def rename(source: Annotated[str, typer.Argument(help="Origin repo to rename from in format xet://[user]/[repo])")],
               dest: Annotated[str, typer.Argument(help="Repo to rename to in format xet://[user]/[repo]")]):
        """
        Forks a new repository from an existing repository.
        """
        fs = XetFS()
        fs.rename_repo(source, dest)

    @staticmethod
    @repo.command()
    def clone(source: Annotated[str, typer.Argument(help="Repository in format xet://[user]/[repo]")],
              args: Annotated[typing.List[str], typer.Argument(help="Arguments to be passed to git-xet clone")] = None):
        """
        Clones a repository on a local path
        """
        return PyxetCLI.clone(source, args)

    @staticmethod
    @repo.command()
    def info(uri: Annotated[str, typer.Argument(help="A URI in format xet://[user]/[repo]")]):
        """
        provide information on the repo\n

        response:\n
        - name: str
        - description: str
        - private: bool
        - created_at: datetime
        - updated_at: datetime
        - pushed_at: datetime
        - branch: str
        - commit_id: str
        - commit_message: str
        - materialize: float
        - stored: float


        """
        raise NotImplementedError("info command is not implemented yet")
