import typer
from typing_extensions import Annotated
import pyxet
import argparse
import fsspec
import sys
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import typing
from tabulate import tabulate
from .file_system import XetFS
from .url_parsing import parse_url
from .rpyxet import rpyxet
from .version import __version__
import subprocess


cli = typer.Typer(add_completion=True, short_help="a pyxet command line interface", no_args_is_help=True)
repo = typer.Typer(add_completion=False, short_help="sub-commands to manage repositories")
branch = typer.Typer(add_completion=False, short_help="sub-commands to manage branches")

cli.add_typer(repo, name="repo")
cli.add_typer(branch, name="branch")

MAX_CONCURRENT_COPIES = threading.Semaphore(32)
CHUNK_SIZE = 16*1024*1024


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
        raise(ValueError(f"Path {s} not in directory {match}"))
    if s[:len(match)] != match:
        raise(ValueError(f"Path {s} not in directory {match}"))
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
        if split[0] == 'xet':
            fs = pyxet.XetFS()
        else:
            fs = fsspec.filesystem(split[0])
            # this is *really* annoying But the s3fs protocol has 
            # protocol as a list ['s3','s3a']
            if isinstance(fs.protocol, list):
                fs.protocol = split[0]
        return fs, split[1]


def _single_file_copy(src_fs, src_path, dest_fs, dest_path,
                     buffer_size=CHUNK_SIZE):
    if dest_path.split('/')[-1] == '.gitattributes':
        print("Skipping .gitattributes as that is required for Xet Magic")
        return
    print(f"Copying {src_path} to {dest_path}...")

    if src_fs.protocol == 'xet' and dest_fs.protocol == 'xet':
        dest_fs.cp_file(src_path, dest_path)
        return
    with MAX_CONCURRENT_COPIES:
        try:
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

def _isdir(fs, path):
    if fs.protocol == 'xet':
        return fs.isdir_or_branch(path)
    else:
        return fs.isdir(path)

def _copy(source, destination, recursive = True, _src_fs=None, _dest_fs=None):
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
            for path,info in src_fs.find(src_path, detail=True).items():
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
                            dest_for_this_path))
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


class PyxetCLI:
    @staticmethod
    @cli.command()
    def login(email: Annotated[str, typer.Option("--email", "-e", help="email address associated with account")],
              user: Annotated[str, typer.Option("--user", "-u", help="user name")],
              password: Annotated[str, typer.Option("--password", "-p", help="password")],
              host: Annotated[str, typer.Option("--host", "-h", help="host to authenticate against")] = "xethub.com",
              force: Annotated[bool, typer.Option("--force", "-f", help="do not perform authentication check and force write to config")] = False,
              no_overwrite: Annotated[bool, typer.Option("--no_overwrite", help="Do not overwrite if existing auth information is found")] = False):
        """
        Configures the login information. Stores the config in ~/.xetconfig
        """
        rpyxet.configure_login(host,user,email,password,force,no_overwrite)

    @staticmethod
    @cli.command()
    def mount(source: Annotated[str, typer.Argument(help="Repository and branch of the form xet://user/repo/branch")],
              path: Annotated[str, typer.Argument(help="Path to mount to. (or a drive letter on windows)")],
              prefetch: Annotated[int, typer.Option(help="Prefetch blocks in multiple of 16MB. Default=2")] = None):
        """
        Mounts a repository on a local path
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

    @staticmethod
    @cli.command(name="mount-curdir", hidden=True)
    def mount_curdir(path: Annotated[str, typer.Argument(help="path to mount to")],
                     autostop: Annotated[bool, typer.Option('--autostop',help="Automatically terminates on unmount")] = False,
                     reference: Annotated[str, typer.Option('--reference', '-r', help="branch or revision to mount")] = 'HEAD',
                     prefetch: Annotated[int, typer.Option('--prefetch', '-p', help="prefetch aggressiveness")] = 16,
                     ip: Annotated[str, typer.Option('--ip',help="IP used to host the NFS server")] = "127.0.0.1",
                     writable: Annotated[bool, typer.Option('--writable',help="Experimental. Do not use")] = False,
                     signal: Annotated[int, typer.Option('--signal',help="Internal:Sends SIGUSR1 to this pid")] = -1):
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
    def clone(source: Annotated[str, typer.Argument(help="Repository and branch of the form xet://user/repo")],
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
    def cp(source: Annotated[str, typer.Argument(help="Source file or folder which will be copied")],
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
    def ls(path: Annotated[str, typer.Argument(help="Source file or folder which will be copied")] = "xet://",
           raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """list files and folders"""
        fs, path = _get_fs_and_path(path)
        try:
            listing = fs.ls(path, detail=True)
            if raw:
                print(listing)
            else:
                print(tabulate(listing, headers="keys"))
            return listing
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def cat(path: Annotated[str, typer.Argument(help="Source file or folder which will be printed")],
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
    def rm(paths: Annotated[typing.List[str], typer.Argument(help="File or folder which will be deleted")],
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
                        print("Cannot delete branches with 'rm' as this is a non-reversible operation and history will not be preserved. Use 'xet branch del'", file=sys.stderr)
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
    def mv(source: Annotated[str, typer.Argument(help="Source Xet file or folder to move")],
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
            print("Unable to move between different protocols {src_fs.protocol}, {dest_fs.protocol}\nYou may want to copy instead", file=sys.stderr)
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
    def info(uri: Annotated[str, typer.Argument(help="a uri of the structure <user>/<project>/<branch>")],
             raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """Provide information about a project branch"""
        fs, path = _get_fs_and_path(uri)
        try:
            info = fs.info(path)
            if raw:
                print(info)
            else:
                print(tabulate([info]))
            return info
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @cli.command()
    def duplicate(source: Annotated[str, typer.Argument(help="origin repo to fork from")],
                  dest: Annotated[str, typer.Argument(help="new repository name")] = None,
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
            dest = "xet://" + fs.get_username() + "/" + repo_name
            print(f"Duplicating to {dest}")
        else:
            repo_name = source.rstrip('/').split('/')[-1]
        fs.duplicate_repo(source, dest)
        try:
            if private:
                print(f"Duplicate Success. Changing permissions...")
                fs.set_repo_attr(dest, "private", True)
                print(f"Repo permissions set successfully")
            if public:
                print(f"Duplicate Success. Changing permissions...")
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
    def make(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
             src_branch: Annotated[str, typer.Argument(help="src branch to copy")],
             dest_branch: Annotated[str, typer.Argument(help="new branch name")]):
        """
        make a new branch copying another branch.
        Branch names with "/" in them are not supported.

        Example: Create a new branch from the main branch

            xet branch make xet://user/repo main new_branch
        """
        fs, remote = _get_fs_and_path(repo)
        assert(fs.protocol == 'xet')
        assert('/' not in dest_branch)
        fs.make_branch(remote, src_branch, dest_branch)

    @staticmethod
    @branch.command()
    def ls(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
             raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """
        list branches of a project.
        """
        fs, path = _get_fs_and_path(repo)
        assert(fs.protocol == 'xet')
        try:
            listing = fs.list_branches(repo, raw)
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
    def delete(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
               branch: Annotated[str, typer.Argument(help="branch to delete")],
               yes: Annotated[bool, typer.Option(help="Say yes to delete")] = False):
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
            assert(fs.protocol == 'xet')
            return fs.delete_branch(repo, branch)
        else:
            print("Add --yes to delete", file=sys.stderr)


    @staticmethod
    @branch.command()
    def info(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
             branch: Annotated[str, typer.Argument(help="branch to query")]):
        """
        Prints information about a branch
        """
        fs, path = _get_fs_and_path(repo)
        assert(fs.protocol == 'xet')
        ret = fs.find_ref(repo, branch)
        print(ret)
        return ret


class RepoCLI:
    @staticmethod
    @repo.command()
    def make(name: Annotated[str, typer.Argument(help="repository name of the form xet://[user]/[repo]")],
             private: Annotated[bool, typer.Option('--private', help="make repository private")] = False,
             public: Annotated[bool, typer.Option('--public', help="make repository public")] = False,
             ):
        """
        make a new empty repository. Either --private or --public must be set
        """
        if private == public:
            print("One of --private or --public must be set")
            return
        fs = XetFS()
        ret = fs.make_repo(name)
        if private:
            print("Creation Success. Changing permissions...")
            fs.set_repo_attr(name, "private", True)
            print("Repo permissions set successfully")
        print(ret)


    @staticmethod
    @repo.command()
    def fork(source: Annotated[str, typer.Argument(help="origin repo to fork from")],
             dest: Annotated[str, typer.Argument(help="new repository name")] = None,
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
            return ls
        except Exception as e:
            print(f"{e}")
            return

    @staticmethod
    @repo.command()
    def rename(source: Annotated[str, typer.Argument(help="origin repo to rename from (of the form xet://user/repo)")],
               dest: Annotated[str, typer.Argument(help="repo to rename to (xet://user/repo)")]):
        """
        Forks a new repository from an existing repository.
        """
        fs = XetFS()
        fs.rename_repo(source, dest)

    @staticmethod
    @repo.command()
    def clone(source: Annotated[str, typer.Argument(help="Repository and branch of the form xet://user/repo")],
              args: Annotated[typing.List[str], typer.Argument(help="Arguments to be passed to git-xet clone")] = None):
        """
        Clones a repository on a local path
        """
        return PyxetCLI.clone(source, args)

    @staticmethod
    @repo.command()
    def info(uri: Annotated[str, typer.Argument(help="A uri of a <user>/<project>")]):
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
