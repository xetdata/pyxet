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
            f"{dir}/*"
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
        # generate a random file in a temp dir
        dir = tempfile.mkdtemp()
        local_files = []
        n_files = 20
        for i in range(n_files):
            file = f"{dir}/data{i}"
            utils.random_binary_file(file, 1024)
            local_files.append(file)
            

        try:
            # test variations of path
            source_list = [
                f"{dir}/*"
            ]

            dest_list = [
            # (dest in cp command, expected path of remote file)
            (f"xet://{user}/{repo}/{b1}", f"xet://{user}/{repo}/{b1}/data"),
            (f"xet://{user}/{repo}/{b1}/", f"xet://{user}/{repo}/{b1}/data"),
            (f"xet://{user}/{repo}/{b1}/zz", f"xet://{user}/{repo}/{b1}/zz"),
        ]
        finally:
            shutil.rmtree(dir)

    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)