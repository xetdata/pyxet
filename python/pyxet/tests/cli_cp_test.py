import os
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
        n_files = 5
        local_files = list(map(lambda i: f"{dir}/data{i}", range(n_files)))
        expected_files = list(map(lambda i: f"xet://{user}/{repo}/{b1}/data{i}", range(n_files)))
        utils.random_binary_files(local_files, [1024] * n_files)
            
        # test variations of path
        source_list = [
            f"{dir}\*"
        ]

        dest_list = [
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            False,
            True,
        ]

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

def test_sub_directory_nonrecursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        
        n_files = 2
        local_files = list(map(lambda i: f"{dir}/data{i}", range(n_files)))
        expected_files = list(map(lambda i: f"xet://{user}/{repo}/{b1}/data{i}", range(n_files)))
        utils.random_binary_files(local_files, [1024] * n_files)

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)

        # test variations of path
        source_list = [
            f"{dir}/*"
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
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files)
                        utils.assert_remote_files_not_exist(f"xet://{user}/{repo}/{b1}/*", f"xet://{user}/{repo}/{b1}/{sub_dir}")
                        pyxet.PyxetCLI.rm(expected_files)
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_sub_directory_recursive_upload():
    user = utils.test_account_login()
    repo = utils.test_repo()
    b1 = utils.new_random_branch_from(f"xet://{user}/{repo}", "main")

    try:
        # generate a mix of random files and directories in a temp dir
        dir = tempfile.mkdtemp()
        
        n_files = 2
        local_files = list(map(lambda i: f"{dir}/data{i}", range(n_files)))
        expected_files_level1 = list(map(lambda i: f"xet://{user}/{repo}/{b1}/data{i}", range(n_files)))
        utils.random_binary_files(local_files, [1024] * n_files)

        sub_dir = "subdir"
        os.mkdir(f"{dir}/{sub_dir}")
        utils.random_binary_file(f"{dir}/{sub_dir}/data", 1024)
        expected_files_level1.append(f"xet://{user}/{repo}/{b1}/{sub_dir}")
        expected_files_level2 = [f"xet://{user}/{repo}/{b1}/{sub_dir}/data"]

        # test variations of path
        source_list = [
            f"{dir}/*"
        ]

        dest_list = [
            f"xet://{user}/{repo}/{b1}",
            f"xet://{user}/{repo}/{b1}/",
        ]

        recursive_list = [
            True,
        ]

        try:
            for src in source_list:
                for dest in dest_list:
                    for r in recursive_list:
                        print(f"xet cp {src} {dest} {r}")
                        pyxet.cli._root_copy(src, dest, "add data", r)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/*", expected_files_level1)
                        utils.assert_remote_files_exist(f"xet://{user}/{repo}/{b1}/{sub_dir}/*", expected_files_level2)
                        pyxet.PyxetCLI.rm(expected_files_level2)
                        pyxet.PyxetCLI.rm(expected_files_level1)
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)
    
def test_directory_nonrecursive_upload():
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
            f"{dir}"
            f"{dir}/"
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
                        utils.assert_remote_files_not_exist(f"xet://{user}/{repo}/{b1}/*", f"xet://{user}/{repo}/{b1}/data")
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)

def test_directory_recursive_upload():
    pass