# File system

Pyxet implements a simple and intuitive API based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library.
Use the same API to access local files, remote files, and files in XetHub. All operations are currently read-only; write functionality 
is in development.

## Using URLs

Xet URLs should be of the form `xet://<repo_user>/<repo_name>/<branch>/<path-to-file>`, where `<path-to-file>` is optional if the URL 
refers to a repository. The xet:// prefix is inferred as needed, or if the URL is given as https://.  

Setting a user and token is required for private repositories. They may be provided as explicit arguments to most pyxet functions, 
or they can be passed in with the URL by prefixing `xet://<user>[:token]@xethub.com/`. For example, 
`xet://user1:mytokenxyz@xethub.com/data_user/data_repo/main/data/survey.csv` would access the file `data/survey.csv` on 
the branch `main` of the repo `data_user/data_repo`  with credentials `user=user1` and `token=mytokenxyz`. 

For example, to refer to the results.csv file in the main branch of the XetHub Flickr30k repo, the following work: 
- `xet://xethub.com/XetHub/Flickr30k/main/results.csv` (all fsspec compatible packages)
- `/XetHub/Flickr30k/main/results.csv` (pyxet.open) 
- `https://xethub.com/XetHub/Flickr30k/main/results.csv` (pyxet.open) 

## pyxet.open

To open a file from an XetHub repository, you can use the `pyxet.open()` function, which takes a file URL in the format 
`xet://<repo_user>/<repo_name>/<branch>/<path-to-file>`.

Example usage of `pyxet.open`:
```sh
  import pyxet

  # Open a file from a public repository.
  f = pyxet.open('xet://xethub.com/XetHub/Flickr30k/main/results.csv')

  # Read the contents of the file.
  contents = f.read()
  f.close()
```

## pyxet.XetFS

To work with a XetHub repository as a file system, you can use the `pyxet.XetFS` class. This class provides a file system handle 
for a XetHub repository, allowing you to perform read-only operations like ls, glob, and open. The initialization of this class 
requires a repository URL and optional arguments for branch, user, and token. 

Example usage of `pyxet.XetFS`:

```sh
  import pyxet

  # Create a file system handle for a public repository.
  fs = pyxet.XetFS('xet://xethub.com/XetHub/Flickr30k/main/')

  # List files in the repository.
  files = fs.ls('/')

  # Open a file from the repository.
  f = fs.open('results.csv')

  # Read the contents of the file.
  contents = f.read()
```

## [fsspec](https://filesystem-spec.readthedocs.io/en/latest/usage.html)

Many packages such as pandas and pyarrow support the fsspec protocol.
xet:// URLs must be used as file paths in these packages. For example, to read a csv from pandas, use:

```sh
  import pyxet
  import pandas as pd

  csv = pd.read_csv('xet://xethub.com/XetHub/Flickr30k/main/results.csv')
```

All fsspec read-only functionality is supported; write operations such as flush() and write() are in development.

## [pathlib](https://docs.python.org/3/library/pathlib.html)

pyxet also implements read-only pathlib functions. `write_text()` and `write_bytes()` are not currently supported.

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
```
