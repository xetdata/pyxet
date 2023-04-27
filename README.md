---

### :construction: :construction: :construction: _pyxet is a new and is under active development. See details below._ :construction: :construction: :construction:

---

<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/images/logo.png" alt="logo" width="400" />
</p>


# pyxet - The SDK for XetHub

[![Version](https://img.shields.io/pypi/v/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Python](https://img.shields.io/pypi/pyversions/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![License](https://img.shields.io/github/license/xetdata/pyxet?style=flat)](https://github.com/xetdata/pyxet/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/pyxet?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Documentation Status](https://readthedocs.org/projects/pyxet/badge/?version=latest)](https://pyxet.readthedocs.io/en/latest/?badge=latest)
[![Discord](https://img.shields.io/discord/1100889165777862807)](https://discord.gg/KCzmjDaDdC)

### Note: This project is just getting started. Please join our [Discord server](https://discord.gg/KCzmjDaDdC) to get involved. To stay informed about updates please star this repo and sign up for [XetHub](https://xethub.com/user/sign_up) to get the newsletter.

## What is it?

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.

## Preliminary Features (more to come, get involved!)

1. A filesystem interface:
    * [fsspec](https://filesystem-spec.readthedocs.io)
        * copy
        * remove
        * list
        * etc.
    * [glob](https://docs.python.org/3/library/glob.html)
    * [pathlib.Path](https://docs.python.org/3/library/pathlib.html)(WIP)

2. Mount:
    * Read-only optimize for speed; perfect for data exploration and analysis and building data-apps and model
      inference.
    * Read-write for data ingestion and preparation; optimal for database backups and training and monitoring logs. _(coming soon)_

3. Integrations:
    - [x] [GitHub](https://github.com) [submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
    - [x] [pandas](https://pandas.pydata.org)
    - [x] [polars](https://pola-rs.github.io/polars-book/)
    - [x] [pyarrow](https://arrow.apache.org/docs/python/)
    - [ ] [duckdb](https://duckdb.org/)
    - [ ] [dask](https://dask.org/)
    - [ ] [ray](https://ray.io/)


## Documentation
For API documentation and full examples, please see [here](https://pyxet.readthedocs.io/en/latest/).

## Getting Started
Assuming you are on a supported OS (MacOS or Linux) and are using a supported version of Python (3.7+), set up your virtualenv with:

```sh
$ python -m venv .venv
...
$ . .venv/bin/activate
```

Then, install pyxet with:

```sh
$ pip install pyxet
```

### Using pyxet
After installing pyxet, next step is to confirm your git configuration is complete.

**Note:** This requirement will be removed soon, but today git user.email and git user.name are required to be set in order to use pyxet. This is because XetHub is built on scalable Git repositories, and pyxet is built with libgit, and libgit requires git user configuration to be set in order to work.

```sh
git config --global user.name "Your Name"
git config --global user.email "your_email_address@email.com"
```

### Demo
To verify that pyxet is working, let's load a CSV file directly into a Pandas dataframe, leveraging pyxet's support for Python fsspec.

```python
import pandas as pd
import pyxet

df = pd.read_csv('xet://xdssio/titanic/main/titanic.csv')
df
```

### Next Steps - Working with private repos (How to set pyxet credentials)
To start working with private repositories, you need to set up credentials for pyxet. The steps to do this are as follows:

1. Sign up for [XetHub](https://xethub.com/user/sign_up)
2. Install [git-xet client](https://xethub.com/explore/install)
3. Create a [Personal Access Token](https://xethub.com/explore/install). Click on 'CREATE TOKEN' button.
4. Copy & Execute Login command, it should look like: `git xet login -u rajatarya -e rajat@xethub.com -p **********`
5. To make these credentials available to pyxet, set the -u param (rajatarya above) and the -p param as XET_USER and XET_TOKEN environment variables. Also, for your python session, `pyxet.login()` will set the environment variables for you.

```sh
# Note: set this environment variable into your shell config (ex. .zshrc) so not lost.
export XET_USER=<YOUR XETHUB USERNAME>
export XET_TOKEN=<YOUR PERSONAL ACCESS TOKEN PASSWORD>
```

```python
import pandas as pd
import pyxet

df = pd.read_csv("xet://xdssio/titanic/main/titanic.csv")  # All files on the platform are available with permissions
# or
pyxet.copy("xet://xdssio/titanic/main/titanic.csv", 'titanic.csv')
```

## Contributing & Getting Help
This project is just getting started. We were so eager to get pyxet out we have not gotten all the code over to this repository yet. We will bring the code here very soon. We fully intend to develop this package in the public under the BSD license. 

In the coming days we will add a roadmap to make it easier to know when pyxet features are being implemented and how you can help.

For now, join our [Discord server](https://discord.gg/KCzmjDaDdC) to talk with us. We have ambitious plans and some very useful features under development / partially working (ex. write back to XetHub repos easy commit messages, stream repositories locally, easily load the same file across git branches, and more).


