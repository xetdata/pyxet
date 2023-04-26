# Mount

A key tool for simplifying working with data and CICD.   
This let you use any tool that works with local files, but with data stored in XetHub.   
Perfect to explore files like images and text, saving monitoring logs, and dump databases data for easy recovery.

```python
import pyxet

fs = pyxet.XetFS("https://xethub.com/username/repo/branch", login=...)
fs.mount("path/to/mount", mode='r')
```

## Best practices

### Read-only mount

There are many cases where one would prefer to mount a repository in read-only mode.
The main benefit is that it is super-fast, no matter the data size, or number of files.

Use cases:

* Explore files like images and text.
* Building dashboard for real-time monitoring.
* Explore datasets with tools which only work with local files.
* Load a machine learning model on a server.

### Read-write mount - coming soon

There are some cases where one would prefer to mount a repository in read-write mode.   
This is significally slower than the read-only mode, but it is still very fast, and maintaining all the goodies of git
behind the scenes.

Use cases:

* Saving model monitoring logs to a folder.
* Saving model checkpoints during training
* Saving Training monitoring logs to a folder.
* Databases which support dumps to storage:
    * [Redis](https://redis.com/)
    * [Postgress](https://www.postgresql.org)
    * Etc.
* Embedded databases:
    * [chromadb](https://github.com/chroma-core/chroma)
    * [sqlite](https://sqlite.org/index.html)
    * [duckdb](https://duckdb.org)

```python
import pyxet

fs = pyxet.XetFS("username/repo/branch", login=...)
fs.mount("path/to/mount", mode='w')
```

### unmount

```python
import pyxet

pyxet.unmount("path/to/mounted")  # or umount?
```