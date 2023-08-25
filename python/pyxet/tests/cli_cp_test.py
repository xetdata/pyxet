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
            (f"xet://{user}/{repo}/{b1}", f"xet://{user}/{repo}/{b1}/data"),
            (f"xet://{user}/{repo}/{b1}/", f"xet://{user}/{repo}/{b1}/data"),
            (f"xet://{user}/{repo}/{b1}/zz", f"xet://{user}/{repo}/{b1}/zz"),
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
                        utils.assert_remote_files_exist(dest[1], [dest[1][6:]])
                        pyxet.PyxetCLI.rm(dest[1])
        finally:
            shutil.rmtree(dir)
    finally:
        pyxet.BranchCLI.delete(f"xet://{user}/{repo}", b1, True)