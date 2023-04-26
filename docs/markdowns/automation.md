# Automation

```python
import pyxet


repo = pyxet.repo("xet://user/repo/branch")
def echo_add(repo):
    print('ADD')
    return repo
repo.git.add('.').echo_add().
```
