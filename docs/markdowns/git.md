# [Git](https://git-scm.com)

Did you ever want to undo a bad schema change?   
To revert a model to a previous version?    
To see the history of your data?

```python
import pyxet

pyxet.create("username/repo", branch="main", login=..., **kwargs) # create a new repo
repo = pyxet.repo("username/repo", branch="main", login=..., **kwargs)
repo.clone(destensation='.', lazy=True)
repo.commit(target='.', message="commit message")
repo.status()
repo.pull()
repo.put(target='.', message="commit message", upstream=True,
         force=False)  # add + commit + push ? do we want this? or is the copy() enough?
repo.checkout(target='.', commit="HEAD~1")
repo.revert(target='.', commit="HEAD~1")
repo.log()
repo.diff()
repo.history()
...
```