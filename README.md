<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/images/logo.png" alt="logo" width="400" />
</p>

# Welcome to pyxet's documentation!

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.   
XetHub is a blob-store with a filesystem like interface and git capabilities, therefore pyxet implement both.

## Features

1. A filesystem interface.
    * [fsspec](https://filesystem-spec.readthedocs.io)
      * copy
      * remove
      * list
      * etc.
    * [glob](https://docs.python.org/3/library/glob.html)
    * [pathlib.Path](https://docs.python.org/3/library/pathlib.html)(WIP) 
2. Mount.
    * Read-only optimize for speed; perfect for data exploration and analysis and building data-apps and model inference.
    * Read-write for data ingestion and preparation; optimal for database backups and training and monitoring logs.
3. Git capabilities:
    * add, commit, push
    * clone, fork
    * merge, rebase
    * pull, fetch
    * checkout, reset
    * stash, diff, log
    * status, branch
    * submodules
      ...
4. Integrations:
    - [x] [pandas](https://pandas.pydata.org)
    - [x] [polars](https://pola-rs.github.io/polars-book/)
    - [x] [pyarrow](https://arrow.apache.org/docs/python/)
    - [ ] [duckdb](https://duckdb.org/)
    - [ ] [dask](https://dask.org/)
    - [ ] [ray](https://ray.io/)
5. CLI: All the features are available through the CLI too under `xet <command>`.

For API documentation and full examples, please see the [documentation](TODO).

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

```python
import pyxet

pyxet.login()  # login using the XETHUB_TOKEN environment variable

pyxet.create("repo", branch="main")  # create a new repo
repo = pyxet.repo("repo", branch="main").clone(destensation='.')

df = pyxet.read_csv("xet://user/repo/branch/path/to/data.csv")  # get data from any place
df.to_csv('data.csv')  # save data to local filesystem - very large files and volumes are supported
# train model 
# ...
model.save('model.pkl')

repo.add_commit_push(target='.', message="commit message")
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
      Have a look at some of
      our [use-cases](https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/markdowns/use_cases.md)

### Basic APIs

```python
import pyxet

fs = pyxet.repo("xet://user/repo/branch")
```

| Command         | python                                                                         | cli                                   |
|-----------------|--------------------------------------------------------------------------------|---------------------------------------|
| **Copy**        | <pre><br/>fs.copy(source, destination)</pre>                                   | <pre>xet cp source destination</pre>  |
| **Move**        | <pre><br/>fs.mv(source, destination)</pre>                                     | <pre>xet mv source destination</pre>  |
| **Remove**      | <pre><br/>fs.rm(path)</pre>                                                    | <pre>xet rm path</pre>                |
| **List**        | <pre><br/>fs.ls(path, new_name)</pre>                                          | <pre>xet ls path</pre>                |
| **Read**        | <pre><br/>with fs.open("path/data.csv", 'r') as f:<br/>    f.readall()</pre>   | <pre>xet cat path</pre>               |
| **Write**       | <pre><br/>with fs.open("path/data.csv", 'w') as f:<br/>    f.write(data)</pre> | <pre> </pre>                          |
| **Mount**       | <pre><br/>fs.mount(dest, lazy=True)</pre>                                      | <pre>xet mount repo dest --lazy</pre> |
| **Unmount**     | <pre><br/>fs.unmount()</pre>                                                   | <pre>xet unmount repo</pre>           |
| **Create repo** | <pre><br/>pyxet.create("repo", branch="main", login=..., **kwargs)</pre>       | <pre>xet create repo -b main</pre>    |
| **Clone**       | <pre><br/>repo.clone(dest, lazy=True)</pre>                                    | <pre>xet clone repo dest --lazy</pre> |

### Git commands

Any git command can be executed using the `repo.git` attribute.

```python
import pyxet

pyxet.git.add("path/to/file")
pyxet.git.commit("commit message")
pyxet.git.push()
pyxet.git.pull()
pyxet.git.status()
...
```

Using the CLI, just use git commands as usual.

### Integrations

* [pandas](https://pandas.pydata.org/)

```python
import pandas as pd

df = pd.read_csv("xet://username/repo/main/data.csv")
df.to_csv("xet://username/repo/main/data.csv", index=False)
```

* [arrow](https://arrow.apache.org/)

```python
import pyxet
import pyarrow.dataset as ds

dataset = ds.dataset("titanic.parquet",
                     filesystem=pyxet.repo("user/repo", "branch"))
```

* [polars](https://polars.rs)

```python
import polars as pl

df = pl.read_csv("xet://username/repo/main/data.csv")

# lazy evaluation
import pyxet
import pyarrow.dataset as ds

lazy_df = pl.scan_parquet(ds.dataset("file.parquet",
                                     filesystem=pyxet.repo("user/repo.branch")))
```

