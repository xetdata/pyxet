import typer
from typing_extensions import Annotated
import pyxet

import sys
import threading
import os
import typing
from tabulate import tabulate
from .file_system import XetFS
from .url_parsing import parse_url
from .version import __version__
import subprocess
from pyxet.config import CHUNK_SIZE
import pyxet.core

cli = typer.Typer(add_completion=True, short_help="a pyxet command line interface", no_args_is_help=True)
repo = typer.Typer(add_completion=False, short_help="sub-commands to manage repositories")
branch = typer.Typer(add_completion=False, short_help="sub-commands to manage branches")

cli.add_typer(repo, name="repo")
cli.add_typer(branch, name="branch")


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
        pyxet.core.configure_login(email, user, password, host, force, no_overwrite)

    @staticmethod
    @cli.command()
    def mount(source: Annotated[str, typer.Argument(help="Repository and branch of the form xet://user/repo/branch")],
              path: Annotated[str, typer.Argument(help="Path to mount to. (or a drive letter on windows)")],
              prefetch: Annotated[int, typer.Option(help="Prefetch blocks in multiple of 16MB. Default=2")] = None):
        """
        Mounts a repository on a local path
        """
        pyxet.core._mount(source, path, prefetch)

    @staticmethod
    @cli.command(name="mount-curdir", hidden=True)
    def mount_curdir(path: Annotated[str, typer.Argument(help="path to mount to")],
                     autostop: Annotated[
                         bool, typer.Option('--autostop', help="Automatically terminates on unmount")] = False,
                     reference: Annotated[
                         str, typer.Option('--reference', '-r', help="branch or revision to mount")] = 'HEAD',
                     prefetch: Annotated[int, typer.Option('--prefetch', '-p', help="prefetch aggressiveness")] = 16,
                     ip: Annotated[str, typer.Option('--ip', help="IP used to host the NFS server")] = "127.0.0.1",
                     writable: Annotated[bool, typer.Option('--writable', help="Experimental. Do not use")] = False,
                     signal: Annotated[int, typer.Option('--signal', help="Internal:Sends SIGUSR1 to this pid")] = -1):
        """
        Internal Do not use
        """
        pyxet.core._perform_mount_curdir(path=path,
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
        if pyxet.core._validate_git_xet() is False:
            print("git-xet not found. Please install git-xet from https://xethub.com/explore/install")
            return
        pyxet.core._clone(source, args)

    @staticmethod
    @cli.command()
    def version():
        """
        Prints the current Xet-cli version
        """
        print(__version__)

    @staticmethod
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
        max_concurrent_copies = threading.Semaphore(parallel)
        pyxet.core._root_copy(source, target, message, recursive=recursive, max_concurrent_copies=max_concurrent_copies)

    @staticmethod
    @cli.command()
    def ls(path: Annotated[str, typer.Argument(help="Source file or folder which will be copied")] = "xet://",
           raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """list files and folders"""
        try:
            listing = pyxet.core._list(path, detail=True)
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
        fs, path = pyxet.core._get_fs_and_path(path)
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
        pyxet.core._rm(paths, message=message)

    @staticmethod
    @cli.command()
    def mv(source: Annotated[str, typer.Argument(help="Source Xet file or folder to move")],
           target: Annotated[str, typer.Argument(help="Target location or name to move to")],
           recursive: Annotated[
               bool, typer.Option("--recursive", "-r", help="Recursively copy files and folders ")] = False,
           message: Annotated[
               str, typer.Option("--message", "-m", help="A commit message")] = ""):
        """move files and folders"""
        pyxet.core._mv(source, target, recursive=recursive, message=message)

    @staticmethod
    @cli.command()
    def info(uri: Annotated[str, typer.Argument(help="a uri of the structure <user>/<project>/<branch>")],
             raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """Provide information about a project branch"""
        try:
            info = pyxet.core._info(uri)
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
        pyxet.core._duplicate(source, dest, private, public, verbose=True)


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
        pyxet.core._make_branch(repo, src_branch, dest_branch)

    @staticmethod
    @branch.command()
    def ls(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
           raw: Annotated[bool, typer.Option(help="If True, will print the raw JSON output")] = False):
        """
        list branches of a project.
        """
        try:
            listing = pyxet.core._list_branches(repo, raw)
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
            return pyxet.core._delete_branch(repo, branch)
        else:
            print("Add --yes to delete", file=sys.stderr)

    @staticmethod
    @branch.command()
    def info(repo: Annotated[str, typer.Argument(help="a repository name <user>/<project>")],
             branch: Annotated[str, typer.Argument(help="branch to query")]):
        """
        Prints information about a branch
        """
        ret = pyxet.core._info_branch(repo, branch)
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
        try:
            repos = pyxet.core._list_repos(raw)
            if raw:
                print(repos)
            else:
                print(tabulate(repos, headers="keys"))
            return
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
        pyxet._rename_repo(source, dest)

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
