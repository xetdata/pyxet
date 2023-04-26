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

fs = pyxet.XetFS("username/repo/branch", login=..., **kwargs)

fs.ls("path/to/dir")
fs.glob("path/to/dir/*")

# Files
with fs.open("path/data.csv", 'b') as f:
    f.read()

    ...

# Write is coming soon
with fs.commit("message"):
    with fs.open("path/file.txt", 'w') as f:
        f.write("Hello, world!")
```

## [pathlib](https://docs.python.org/3/library/pathlib.html)

```python
from pyxet.pathlib import Path

path = Path("https://xethub.com/xdssio/titanic.git/main/titanic.csv")
path.is_dir()
path.is_file()
path.exists()
path.read_bytes()
path.read_text()
path.absolute()
path.iterdir()
path.joinpath()  # returns a new path
path.glob()  # use fsspec glob
# work-in-progress
path.write_text("text")
path.write_bytes(b"text")
```
