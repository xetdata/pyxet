import pytest


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


def require_s3_creds():
    """
    Function to help mark any tests that need credentials to S3 to work.
    For example, many of the sync tests may want this.

    Returns a pytest mark with a skipif condition to be evaluated during
    test collection. Will check if AWS credentials have been defined as
    environment variables (i.e. AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
    """

    def try_load_s3():
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        try:
            s3 = boto3.client('s3')
            _ = s3.list_buckets()
            return True
        except (NoCredentialsError, ClientError):
            print(f'No Credentials')
            return False

    msg = "AWS credentials not defined"
    return pytest.mark.skipif(not try_load_s3(), reason=msg)


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
    TESTING_SYNCREPO = f"{TESTING_USERNAME}/sync_test"
    FLICKR_CSV = "xet://XetHub/Flickr30k/main/results.csv"
    S3_BUCKET = "pyxet-test"
