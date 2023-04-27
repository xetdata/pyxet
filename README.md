---

### :construction: pyxet is a new and is under active development. It is not ready for production usage. See details below. :construction: 

---

<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/images/logo.png" alt="logo" width="400" />
</p>


# pyxet - The SDK for XetHub

[![Version](https://img.shields.io/pypi/v/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Python](https://img.shields.io/pypi/pyversions/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![License](https://img.shields.io/pypi/l/pyxet.svg?style=flat)](https://github.com/xetdata/pyxet/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/pyxet?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Discord](https://img.shields.io/discord/1100889165777862807)](https://discord.gg/KCzmjDaDdC)

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.   
XetHub is a blob-store with a filesystem like interface and git capabilities, therefore pyxet implement both.

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

## Usage

### Quickstart

#### Start by creating a new repo and clone it to your local filesystem.

```python
import pyxet

pyxet.login()  # login using the XETHUB_TOKEN environment variable

pyxet.create("<user>/tutorial", branch="main")  # create a new repo
repo = pyxet.repo("user/tutorial", branch="main").clone(destensation='.')
```

#### Getting data

```python
import pandas as pd
import pyxet

df = pd.read_csv("xet://xdssio/titanic/main/titanic.csv")  # All files on the platform are available with permissions
# or
pyxet.copy("xet://xdssio/titanic/main/titanic.csv", 'titanic.csv')
```

#### Training a model

We will assume that we have a model training script `train.py` which saves the model as `model.pkl`.

* Checkout this [titanic app](https://xethub.com/xdssio/titanic-server-example) for example.

#### Uploading - committing

* This will work on **any file size, and any volume of data**.
* We can upload the data, model, metrics, etc.

```python
import pyxet

# filesystem interface
repo = pyxet.repo("user/repo/user/branch")
with repo.commit("commit message"):
    with repo.open('model.pkl', 'wb') as f:
        f.write(model_bytes)

# pathlib interface
from pyxet.pathlib import Path

Path('https://xethub.com/user/repo/branch/model.pkl').write_bytes(model_bytes)

# git interface 
with repo.open('model.pkl', 'wb') as f:
    f.write(model_bytes)
repo.add('model.pkl').commit('commit-message').push(upstream='HEAD')
```

Or using standard git commands:

```bash
git add . && git commit -m "commit message" && git push
```

### Next steps

* Now we can branch the repo and continue working on the model.
    * We can manage model versions using git - no need to save models in different files.
* We
  can [upload](https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/markdowns/filesystem.md)
  more data and continue training the model.
* We can save model training results and metrics
  using [mount](https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/markdowns/mount.md)
* Collaborate
    * MLOps engineers which can mount the models and use them for inference.
    * MLOps engineers which can add a docker-image and save it too.
    * Data-scientists can build gradio apps which are available as endpoints automatically (WIP)
    * Machine learning engineers can create feature stores, build datasets, models, and combines datasets.
* Have a look at some
  more [use-cases](https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/markdowns/use_cases.md)

### Basic APIs

```python
import pyxet

fs = pyxet.repo("xet://user/repo/branch")
```

| Command         | State | python                                                                                                           | CLI                                   |
|-----------------|-------|------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| **Copy**        | `-`   | <pre><br/>fs.copy(source, destination)</pre>                                                                     | <pre>xet cp source destination</pre>  |
| **Move**        | `-`   | <pre><br/>fs.mv(source, destination)</pre>                                                                       | <pre>xet mv source destination</pre>  |
| **Remove**      | `-`   | <pre><br/>fs.rm(path)</pre>                                                                                      | <pre>xet rm path</pre>                |
| **List**        | `+`   | <pre><br/>fs.ls(path, new_name)</pre>                                                                            | <pre>xet ls path</pre>                |
| **Read**        | `+`   | <pre><br/>with fs.open("path/data.csv", 'r') as f:<br/>    f.read()</pre>                                     | <pre>xet cat path</pre>               |
| **Write**       | `+`   | <pre>with fs.commit("message"):<br/>    with fs.open("path/data.csv", 'w') as f:<br/>        f.write(data)</pre> | <pre> </pre>                          |
| **Mount**       | `-`   | <pre><br/>fs.mount(dest, lazy=True)</pre>                                                                        | <pre>xet mount repo dest --lazy</pre> |
| **Unmount**     | `-`   | <pre><br/>fs.unmount()</pre>                                                                                     | <pre>xet unmount repo</pre>           |
| **Create repo** | `-`   | <pre><br/>pyxet.create("repo", branch="main", login=..., **kwargs)</pre>                                         | <pre>xet create repo -b main</pre>    |
| **Clone**       | `-`   | <pre><br/>repo.clone(dest, lazy=True)</pre>                                                                      | <pre>xet clone repo dest --lazy</pre> |
| **Fork**        | `-`   | <pre><br/>repo.fork(dest, lazy=True)</pre>                                                                       |                                       |

### Git commands [WIP]

Any git command can be executed using the `repo.git` attribute.

```python
import pyxet

repo = pyxet.Git("xet://user/repo/branch")
repo.add("path/to/file")
repo.commit("commit message")
repo.push()
repo.pull()
repo.status()
...
```

Using the CLI, just use git commands as usual.

### Integrations

* [pandas](https://pandas.pydata.org/)

```python
import pandas as pd
import pyxet
df = pd.read_csv("xet://username/repo/main/data.csv")
with pyxet.repo("username/repo/branch").commit("commit message"):
    df.to_csv("xet://username/repo/main/data.csv", index=False)
```

* [Arrow](https://arrow.apache.org/)

```python
import pyxet
import pyarrow.dataset as ds

dataset = ds.dataset("titanic.parquet",
                     filesystem=pyxet.repo("user/repo", "branch"))
```

* [Polars](https://polars.rs)

```python
import polars as pl

df = pl.read_csv("xet://username/repo/main/data.csv")

# lazy evaluation
import pyxet
import pyarrow.dataset as ds

lazy_df = pl.scan_parquet(ds.dataset("file.parquet",
                                     filesystem=pyxet.repo("user/repo.branch")))
```

# Project examples

* [Titanic-app](https://xethub.com/xdssio/titanic-server-example)
