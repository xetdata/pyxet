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
    min_version: str or None, default None
        Optional minimum version of the package.
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


class CONSTANTS:
    TITANIC_CSV = "https://xethub.com/xdssio/titanic.git/main/titanic.csv"
    TITANIC_PARQUET = "https://xethub.com/xdssio/titanic.git/main/titanic.parquet"
    TITANIC_JSON = "https://xethub.com/xdssio/titanic.git/main/titanic.json"
    TITANIC_MAIN = "https://xethub.com/xdssio/titanic.git/main"
    TITANIC_MOUNT = "xet@xethub.com:xdssio/titanic.git"

    FLICKR_CSV = "https://xethub.com/XetHub/Flickr30k.git/main/results.csv"
