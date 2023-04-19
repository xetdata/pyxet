# Quickstart
[XetHub](https://xethub.com/) is a cloud storage with git capabilities. It is a great place to store your data, models, logs and code.    
This library allows you to access XetHub from Python.

## Installation

`pip install pyxet`

## [Filesystem (fsspec)](https://filesystem-spec.readthedocs.io/en/latest/usage.html)
* [copy conventions](https://filesystem-spec.readthedocs.io/en/latest/copying.html)
```python
import pyxet

fs = pyxet.repo("username/repo", branch="main", login=..., **kwargs)

fs.ls("path/to/dir")
fs.cat("path/to/file")
fs.copy("path/to/file-or-folder", "path/to/dest")
fs.mv("path/to/file-or-folder", "path/to/dest")
fs.rm("path/to/file-or-folder", "path/to/dest")
fs.exists("/remote/output/success")
fs.isfile("/remote/output/success")
fs.isdir("/remote/output/success")
fs.glob("path/to/dir/*")


with fs.open("path/data.csv", 'r') as f:
    f.readlines()
    f.readline()
    ...

with fs.open("path/file.txt", 'w') as f:
    f.write("Hello, world!")
```
### Mount
A key tool for simplifying working with data and CICD.   
This let you use any tool that works with local files, but with data stored in XetHub.   
Perfect to explore files like images and text, saving monitoring logs, and dump databases data for easy recovery.
```python
import pyxet

fs = pyxet.repo("username/repo", branch="main", login=..., **kwargs)
fs.mount("path/to/mount", mode='r', lazy=True)
fs.umount("path/to/mount")
```

## [Git](https://git-scm.com)
Did you ever want to undo a bad schema change? Or to revert a model to a previous version? Or to see the history of your data?
```python
import pyxet

repo = pyxet.repo("username/repo", branch="main", login=..., **kwargs)
repo.clone(destensation='.', lazy=True)
repo.commit(target='.', message="commit message")
repo.status()
repo.pull()
repo.put(target='.', message="commit message", upstream=True, force=False) # add + commit + push ? do we want this? or is the copy() enough?
repo.checkout(target='.', commit="HEAD~1")
repo.revert(target='.', commit="HEAD~1")
repo.log()
repo.diff()
...
```

## Integrations
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
                     filesystem=pyxet.repo("user/repo","branch"))
```
* [polars](https://polars.rs)
```python
import polars as pl

df = pl.read_csv("xet://username/repo/main/data.csv")

# lazy evaluation
import pyxet
import pyarrow.dataset as ds
lazy_df = pl.scan_parquet(ds.dataset("titanic.parquet", 
                                     filesystem=pyxet.repo("user/repo","branch")))
```

## CLI
For quick and dirty access to XetHub.
```bash
xet clone username/repo --lazy ...
xet ls username/repo/branch
xet cp source dest
xet mv source dest
xet rm path
xet login
```