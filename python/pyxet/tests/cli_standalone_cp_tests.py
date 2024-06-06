import os
import pytest
import pyxet
import utils
import shutil
import tempfile
import subprocess
import sys

from pyxet.file_operations import perform_copy, build_cp_action_list

# Set these once.
user, host = utils.test_account_login()
repo = utils.test_repo()

# TODO: right syntax for this.
xet_cli_path=os.environ.get("XET_STANDALONE_CLI", None)

if xet_cli_path is None:
    print("Warning: XET_STANDALONE_CLI not set, skipping all tests.")

def xet_url(branch = None, path = None): 
    ret = f"xet://{host}:{user}/{repo}"
    if branch is not None:
        ret += f"/{branch}"
    if path is not None:
        assert branch is not None
        ret += f"/{path}"
    return ret

def run_xet(*args, cwd = None):
    arg_text = ' '.join(f'"{arg}"' if arg.contains(' ') else arg for arg in args)
    print(f"Running command:  xet {arg_text}")
    subprocess.check_output([xet_cli_path] + args, cwd = cwd)

def xet_perform_copy(cwd, src, dest, message, is_recursive):
    run_xet(["cp"] + (["--recursive"] if is_recursive else []) + [src, dest], cwd=cwd)

def delete_branch(branch): 
    try:
        run_xet("branch", "delete", xet_url(branch))
    except Exception as e:
        print(f"WARNING: Exception trying to delete branch {branch} on {repo}: {e}")


@pytest.mark.skipif(xet_cli_path is None)
def test_single_file_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")
    
    try:
        # generate a random file in a temp dir
        dir = tempfile.mkdtemp()
        local_file = f"{dir}/data"
        utils.random_binary_file(local_file, 1024)

        # test variations of path
        source_list = [
            f"{dir}/data",
        ]

        dest_list = [
            # (dest in cp command, expected path of remote file)
            (f"xet://{host}:{user}/{repo}/{b1}", [f"xet://{host}:{user}/{repo}/{b1}/data"]),
            (f"xet://{host}:{user}/{repo}/{b1}/",[f"xet://{host}:{user}/{repo}/{b1}/data"]),
            (f"xet://{host}:{user}/{repo}/{b1}/zz", [f"xet://{host}:{user}/{repo}/{b1}/zz"]),
        ]

        recursive_list = [
            False,
            True,
        ]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        xet_perform_copy(src, dest[0], "add data", r)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", dest[1])
                        pyxet.PyxetCLI.rm(dest[1])
        finally:
            shutil.rmtree(dir)
    finally:
        delete_branch(b1)

@pytest.mark.skipif(xet_cli_path is None)
def test_multiple_files_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")

    try:
        # generate random files in a temp dir
        dir = tempfile.mkdtemp()
        local_files = [f"{dir}/data0", f"{dir}/data1"]
        utils.random_binary_files(local_files, [1024, 1024])
            
        # test variations of path
        source_list = [
            f"{dir}/*",
        ]

        dest_list = [
            f"xet://{host}:{user}/{repo}/{b1}",
            f"xet://{host}:{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
            True,
        ]

        expected_files = [f"xet://{host}:{user}/{repo}/{b1}/data0", f"xet://{host}:{user}/{repo}/{b1}/data1"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        xet_perform_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", expected_files)
                        run_xet("rm", *expected_files)
        finally:
            shutil.rmtree(dir)
    finally:
        delete_branch(b1)

@pytest.mark.skipif(xet_cli_path is None)
def test_glob_nonrecursive_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")

    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        
        local_files = [f"{dir}/data0", f"{dir}/data1"]
        utils.random_binary_files(local_files, [1024, 1024])

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)

        # test variations of path
        source_list = [
            f"{dir}/*",
        ]

        dest_list = [
            f"xet://{host}:{user}/{repo}/{b1}",
            f"xet://{host}:{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
        ]

        expected_files = [f"xet://{host}:{user}/{repo}/{b1}/data0", f"xet://{host}:{user}/{repo}/{b1}/data1"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        xet_perform_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", expected_files)
                        utils.assert_remote_files_not_exist(f"xet://{host}:{user}/{repo}/{b1}/*", [f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}"])
                        run_xet("rm", *expected_files)
        finally:
            shutil.rmtree(dir)
    finally:
        delete_branch(b1)

@pytest.mark.skipif(xet_cli_path is None)
def test_glob_recursive_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")

    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        
        local_files = [f"{dir}/data0", f"{dir}/data1"]
        utils.random_binary_files(local_files, [1024, 1024])

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)
        
        # test variations of path
        source_list = [
            f"{dir}/*",
        ]

        dest_list = [
            f"xet://{host}:{user}/{repo}/{b1}",
            f"xet://{host}:{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        expected_files_level1 = [f"xet://{host}:{user}/{repo}/{b1}/data0", f"xet://{host}:{user}/{repo}/{b1}/data1", f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}"]
        expected_files_level2 = [f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}/data"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        xet_perform_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}/*", expected_files_level2)
                        run_xet("rm", *expected_files_level1)
        finally:
            shutil.rmtree(dir)
    finally:
        delete_branch(b1)
    
@pytest.mark.skipif(xet_cli_path is None)
def test_directory_nonrecursive_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")

    try:
        # generate a random file in a temp dir
        dir = tempfile.mkdtemp()
        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        local_file = f"{dir}/{sub_dir}/data"
        utils.random_binary_file(local_file, 1024)

        # test variations of path
        source_list = [
            (f"{dir}/{sub_dir}/data", True),
            (f"{dir}/{sub_dir}", False),
            (f"{dir}/{sub_dir}/", False)
        ]

        dest_list = [
            f"xet://{host}:{user}/{repo}/{b1}",
            f"xet://{host}:{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
        ]

        try:
            for src, should_succeed in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        
                        if should_succeed:
                            xet_perform_copy(src, dest, "add data", r)
                                
                            utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", [f"xet://{host}:{user}/{repo}/{b1}/data"])

                        else:

                            # ignores instead of raising error
                            xet_perform_copy(src, dest, "add data", r)

        finally:
            shutil.rmtree(dir)
    finally:
        delete_branch(b1)

@pytest.mark.skipif(xet_cli_path is None)
def test_directory_recursive_upload():
    b1 = utils.new_random_branch_from(f"xet://{host}:{user}/{repo}", "main")
    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        
        local_files = [f"{dir}/data0", f"{dir}/data1"]
        utils.random_binary_files(local_files, [1024, 1024])

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)

        # test variations of path
        source_list = [
            f"{dir}/*",
        ]

        dest_list = [
            f"xet://{host}:{user}/{repo}/{b1}",
            f"xet://{host}:{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        expected_files_level1 = [f"xet://{host}:{user}/{repo}/{b1}/data0", f"xet://{host}:{user}/{repo}/{b1}/data1", f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}"]
        expected_files_level2 = [f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}/data"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        xet_perform_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{host}:{user}/{repo}/{b1}/{sub_dir}/*", expected_files_level2)
                        run_xet("rm", *expected_files_level1)
                        run_xet("rm", *expected_files_level2)
        finally:
            shutil.rmtree(dir)
        
    finally:
        delete_branch(b1) 