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

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.

### Note: This project is just getting started. Please join our [Discord server](https://discord.gg/KCzmjDaDdC) to get involved. To stay informed about updates please star this repo and sign up for [XetHub](https://xethub.com/user/sign_up) to get the newsletter.

## Features

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

For API documentation and full examples, please see the [documentation](https://pyxet.readthedocs.io/en/latest/).

## Getting Started



## Installation

`pip install pyxet`

## Environment Setup

* This is only done for the first time.

1. [Create an account or sign in](https://xethub.com/assets/docs/getting-started/installation#create-a-xethub-account)
2. [Install the git-xet CLI](https://xethub.com/assets/docs/getting-started/installation#install-the-git-xet-extension)
3. Get a personal access token [here](https://xethub.com/user/settings/pat)
4. Install the [pyxet](https://pypi.org/project/pyxet/) library
5. Authenticate in one of two ways:
    1. Set you personal access token as `XETHUB_TOKEN` environment variable.
    2. Configure using the CLI
       command [git-xet login](https://xethub.com/assets/docs/getting-started/installation#configure-authentication)

## Using pyxet

### Quickstart

#### Getting data

```python
import pandas as pd
import pyxet

df = pd.read_csv("xet://xdssio/titanic/main/titanic.csv")  # All files on the platform are available with permissions
# or
pyxet.copy("xet://xdssio/titanic/main/titanic.csv", 'titanic.csv')
```

## Getting Help
