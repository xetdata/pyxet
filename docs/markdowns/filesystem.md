# File system

The filesystem APIs are the most straight forward.     
They are based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library. This means that you can use
the same API to access local files, remote files, and files in Xethub.

## [Filesystem (fsspec)](https://filesystem-spec.readthedocs.io/en/latest/usage.html)

* [Copy conventions](https://filesystem-spec.readthedocs.io/en/latest/copying.html)

The `pyxet.repo` returns a repository-filesystem that can be used with fsspec.   
It works both like a normal filesystem and git.
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

# Files
with fs.open("path/data.csv", 'r') as f:
    f.readlines()
    f.readline()
    f.readall()
    ...

with fs.open("path/file.txt", 'w') as f:
    f.write("Hello, world!")
```

### Summaries (Nice to have)

```python
fs.info()
{"name": "username/repo",
 "size": 1234,
 "type": "repository",
 "created": "2021-01-01",
 "modified": "2021-01-01",
 "materialized": 1.2,
 "stored": 0.001}

fs.info("titanic.csv")
{"name": "titanic.csv",
 "size": 1234,
 "type": "file",
 "created": "2021-01-01",
 "modified": "2021-01-01", }

fs.show("titanic.csv")  # csv sketch
fs.show("viz.json")  # visualisation render
# Alternatives visualize, plot, view, render, display, ...
```

## [pathlib](https://docs.python.org/3/library/pathlib.html) (Nice to have)

```python
from pyxet.pathlib import Path

path = Path("https://xethub.com/xdssio/titanic.git/main/titanic.csv")
path.is_dir()
path.is_file()
path.exists()
path.read_bytes()
path.read_text()
path.write_text("text")  # TODO
path.write_bytes(b"text")  # TODO
path.parent  # returns a new path
path.absolute()
path.iterdir()
path.joinpath()  # returns a new path
path.glob()
```

## [glob](https://docs.python.org/3/library/glob.html) (Nice to have)

```python
from pyxet.glob import glob, iglob

iglob("https://xethub.com/xdssio/titanic.git/main/data/*.csv")

```