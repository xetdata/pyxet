## pyxet.XetFS

To work with a XetHub repository as a file system, you can use the `pyxet.XetFS` class which builds on [`fsspec`](https://github.com/fsspec/filesystem_spec) 

This class provides a file system handle for a XetHub repository, allowing you
to perform operations like ls, glob, open, write, copy, put, etc. 

Example read usage of `pyxet.XetFS` on public repos:

```python
  import pyxet

  # Create a file system handle for a public repository.
  fs = pyxet.XetFS()

  # List files in the repository.
  files = fs.ls('XetHub/Flickr30k/main/')

  # Open a file from the repository.
  f = fs.open('XetHub/Flickr30k/main/results.csv')

  # Read the contents of the file.
  contents = f.read()

  # download a file
  fs.get('XetHub/Flickr30k/main/results.csv', '/tmp/results.csv')

```

Example modifications on a private repo after logging in and creating a transaction scope. Note that the files that are modified are
always present within the scope of the transaction.

```python
  import pyxet

  fs = pyxet.XetFS()
  with fs.transaction('my-username/my-repo/main', 'write a file'):
    file = fs.open('my-username/my-repo/main/hello/world.txt', 'w')
    file.write('hello world')
    file.close()

  with fs.transaction('my-username/my-repo/main', 'copy a directory from remote to remote'):
    fs.copy('my-username/my-repo/main/hello/', 'my-username/my-repo/main/hullo/', recursive=True)

  with fs.transaction('my-username/my-repo/main', 'putting files from recursively from local directory to the repo'):
    fs.put('/tmp/foo', 'my-username/my-repo/main/baz', recursive=True)

```


Many packages such as pandas and pyarrow support the fsspec protocol.
xet:// URLs must be used as file paths in these packages. For example, to read a csv from pandas, use:

```sh
  import pyxet
  import pandas as pd

  csv = pd.read_csv('xet://xethub.com/XetHub/Flickr30k/main/results.csv')
```

All fsspec read-only functionality is supported; write operations such as flush() and write() are in development.