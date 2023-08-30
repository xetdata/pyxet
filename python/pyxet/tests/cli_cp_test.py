import os
import pytest
import pyxet
import utils
import shutil
import tempfile


def test_single_file_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")
    
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
            (f"xet://{user}/{repo}/{b1}", [f"xet://{user}/{repo}/{b1}/data"]),
            (f"xet://{user}/{repo}/{b1}/",[f"xet://{user}/{repo}/{b1}/data"]),
            (f"xet://{user}/{repo}/{b1}/zz", [f"xet://{user}/{repo}/{b1}/zz"]),
        ]

        recursive_list = [
            False,
            True,
        ]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest[0]} {r}")
                        pyxet.cli._root_copy(src, dest[0], "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", dest[1])
                        pyxet.PyxetCLI.rm(dest[1])
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_multiple_files_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

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
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
            True,
        ]

        expected_files = [f"xet://{user}/{repo}/{b1}/data0", f"xet://{user}/{repo}/{b1}/data1"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files)
                        pyxet.PyxetCLI.rm(expected_files)
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_glob_nonrecursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

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
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
        ]

        expected_files = [f"xet://{user}/{repo}/{b1}/data0", f"xet://{user}/{repo}/{b1}/data1"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files)
                        utils.assert_remote_files_not_exist(f"xet://{user}/{repo}/{b1}/*", [f"xet://{user}/{repo}/{b1}/{sub_dir}"])
                        pyxet.PyxetCLI.rm(expected_files)
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_glob_recursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

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
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        expected_files_level1 = [f"xet://{user}/{repo}/{b1}/data0", f"xet://{user}/{repo}/{b1}/data1", f"xet://{user}/{repo}/{b1}/{sub_dir}"]
        expected_files_level2 = [f"xet://{user}/{repo}/{b1}/{sub_dir}/data"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/{sub_dir}/*", expected_files_level2)
                        pyxet.PyxetCLI.rm(expected_files_level1)
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)
    
@pytest.mark.skip(reason="fix in a future PR")
def test_directory_nonrecursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

    try:
        # generate a random file in a temp dir
        dir = tempfile.mkdtemp()
        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        local_file = f"{dir}/{sub_dir}/data"
        utils.random_binary_file(local_file, 1024)

        # test variations of path
        source_list = [
            f"{dir}/{sub_dir}",
            f"{dir}/{sub_dir}/",
        ]

        dest_list = [
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
        ]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_not_exist(f"xet://{user}/{repo}/{b1}/*", [f"xet://{user}/{repo}/{b1}/{sub_dir}"])
                        utils.assert_remote_files_not_exist(f"xet://{user}/{repo}/{b1}/*", [f"xet://{user}/{repo}/{b1}/data"])
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_directory_recursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")
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
            f"{dir}/",
        ]

        dest_list = [
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        expected_files_level1 = [f"xet://{user}/{repo}/{b1}/data0", f"xet://{user}/{repo}/{b1}/data1", f"xet://{user}/{repo}/{b1}/{sub_dir}"]
        expected_files_level2 = [f"xet://{user}/{repo}/{b1}/{sub_dir}/data"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/{sub_dir}/*", expected_files_level2)
                        pyxet.PyxetCLI.rm(expected_files_level1)
        finally:
            shutil.rmtree(dir)
        
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

# According to https://filesystem-spec.readthedocs.io/en/latest/copying.html#single-source-to-single-target
# section 1e, if the trailing slash is omitted from "source/subdir" then the subdir is also copied, 
# not just its contents.
def test_directory_recursive_noslash_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")
    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        dir_name = os.path.basename(dir)
        
        local_files = [f"{dir}/data0", f"{dir}/data1"]
        utils.random_binary_files(local_files, [1024, 1024])

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)

        # test variations of path
        source_list = [
            f"{dir}",
        ]

        dest_list = [
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        expected_files_level1 = [f"xet://{user}/{repo}/{b1}/{dir_name}"]
        expected_files_level2 = [f"xet://{user}/{repo}/{b1}/{dir_name}/data0", f"xet://{user}/{repo}/{b1}/{dir_name}/data1", f"xet://{user}/{repo}/{b1}/{dir_name}/{sub_dir}"]
        expected_files_level3 = [f"xet://{user}/{repo}/{b1}/{dir_name}/{sub_dir}/data"]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/{dir_name}/*", expected_files_level2)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/{dir_name}/{sub_dir}/*", expected_files_level3)
                        pyxet.PyxetCLI.rm(expected_files_level1)
        finally:
            shutil.rmtree(dir)
        
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)