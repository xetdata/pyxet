import fsspec
import os
import pytest
import pyxet
import random
import secrets
import string



def safe_import(mod_name: str):
    """
    Parameters
    ----------
    mod_name : str
        Name of the module to be imported
    Returns
    -------
    object
        The imported module if successful, or False
    """
    try:
        mod = __import__(mod_name)
    except ImportError:
        return False
    except SystemError:
        # TODO: numba is incompatible with numpy 1.24+.
        # Once that's fixed, this block should be removed.
        if mod_name == "numba":
            return False
        else:
            raise

    return mod


def skip_if_no(package: str):
    """
    Generic function to help skip tests when required packages are not
    present on the testing system.
    This function returns a pytest mark with a skip condition that will be
    evaluated during test collection. An attempt will be made to import the
    specified ``package`` and optionally ensure it meets the ``min_version``
    The mark can be used as either a decorator for a test function or to be
    applied to parameters in pytest.mark.parametrize calls or parametrized
    fixtures.
    If the import and version check are unsuccessful, then the test function
    (or test case when used in conjunction with parametrization) will be
    skipped.
    Parameters
    ----------
    package: str
        The name of the required package.
    Returns
    -------
    _pytest.mark.structures.MarkDecorator
        a pytest.mark.skipif to use as either a test decorator or a
        parametrization mark.
    """
    msg = f"Could not import '{package}'"
    return pytest.mark.skipif(
        not safe_import(package), reason=msg
    )

def test_user_info():
    user = os.getenv('XET_TEST_USER')
    assert user is not None
    email = os.getenv('XET_TEST_EMAIL')
    assert email is not None
    token = os.getenv('XET_TEST_TOKEN')
    assert token is not None

    return {
        "user": user,
        "email": email,
        "token": token,
    }

def test_repo():
    repo = os.getenv('XET_TEST_REPO')
    assert repo is not None
    return repo

def test_account_login():
    user_info = test_user_info()
    pyxet.login(user_info['user'], user_info['token'], user_info['email'])
    return user_info['user']

def random_string(N):
    return ''.join(secrets.choice(string.ascii_letters + string.digits)
              for i in range(N))

def random_binary_file(path, size):
    with open(path, 'wb') as fout:
        fout.write(os.urandom(size))

def random_text_file(path, size):
    chars = ''.join([random.choice(string.printable) for i in range(size)])
    with open(path, 'w') as f:
        f.write(chars)

def random_binary_files(path_list, size_list):
    for p, s in zip(path_list, size_list):
        random_binary_file(p, s)


# Make a random branch copying src_branch in repo in format xet://[user]/[repo],
# returns the new branch name
def new_random_branch_from(repo, src_branch):
    dest_branch = random_string(20)
    pyxet.BranchCLI.make(repo, src_branch, dest_branch)
    return dest_branch

def assert_remote_files_exist(remote, expected):
    fs = fsspec.filesystem("xet")
    listing = fs.glob(remote, detail=False)
    print(listing)
    print(expected)
    for i in expected:
        assert i.removeprefix("xet://") in listing

def assert_remote_files_not_exist(remote, not_expected):
    fs = fsspec.filesystem("xet")
    listing = fs.glob(remote, detail=False)
    print(listing)
    print(not_expected)
    for i in not_expected:
        assert i.removeprefix("xet://") not in listing


class CONSTANTS:
    TITANIC_CSV = "xet://xdssio/titanic/main/titanic.csv"
    TITANIC_XET_CSV = "xet://xdssio/titanic/main/titanic.csv"
    TITANIC_PARQUET = "xet://xdssio/titanic/main/titanic.parquet"
    TITANIC_JSON = "xet://xdssio/titanic/main/titanic.json"
    TITANIC_MAIN = "xet://xdssio/titanic/main"
    TITANIC_TEMPFILE = "xet://xdssio/titanic/main/tempfile.txt"
    TESTING_USERNAME = "_xethub_testing_account"
    TESTING_TOKEN = "q8HnHwaw6hw3zhJNuUjAnw"
    TESTING_TEMPREPO_ROOT = "_xethub_testing_account/read_write_testing"
    TESTING_TEMPREPO = "_xethub_testing_account/read_write_testing/main"
    FLICKR_CSV = "xet://XetHub/Flickr30k/main/results.csv"
