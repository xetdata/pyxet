# Quick Start

[XetHub](https://xethub.com/) is a cloud storage platform with Git capabilities. It is a great place to store your data,
models,
logs, and code. The pyxet library allows you to easily access XetHub from Python.

## Installation

Assuming you are on a supported OS (MacOS or Linux) and are using a supported version of Python (3.7+), set up your
virtualenv with:

```sh
$ python -m venv .venv
...
$ . .venv/bin/activate
```

Then, install pyxet with:

```sh
$ pip install pyxet
```

### Demo

To verify that pyxet is working, let's load a CSV file directly into a Pandas dataframe, leveraging pyxet's support for
Python fsspec.

```python
# assumes you have already done pip install pandas
import pyxet  # make xet:// protocol available
import pandas as pd

df = pd.read_csv('xet://xdssio/titanic/main/titanic.csv')
df
```

should return something like:

```
Out[3]:
     PassengerId  Survived  Pclass  ...     Fare Cabin  Embarked
0              1         0       3  ...   7.2500   NaN         S
1              2         1       1  ...  71.2833   C85         C
2              3         1       3  ...   7.9250   NaN         S
3              4         1       1  ...  53.1000  C123         S
4              5         0       3  ...   8.0500   NaN         S
..           ...       ...     ...  ...      ...   ...       ...
886          887         0       2  ...  13.0000   NaN         S
887          888         1       1  ...  30.0000   B42         S
888          889         0       3  ...  23.4500   NaN         S
889          890         1       1  ...  30.0000  C148         C
890          891         0       3  ...   7.7500   NaN         Q

[891 rows x 12 columns]
```

### Next Steps - Working with private repos (How to set pyxet credentials)

To start working with private repositories, you need to set up credentials for pyxet. The steps to do this are as
follows:

1. Sign up for [XetHub](https://xethub.com/user/sign_up)
2. Install [git-xet client](https://xethub.com/explore/install)
3. Create a [Personal Access Token](https://xethub.com/user/settings/pat). Click on 'CREATE TOKEN' button.
4. Copy & Execute Login command, it should look like: `git xet login -u rajatarya -e rajat@xethub.com -p **********`
5. To make these credentials available to pyxet, set the -u param (rajatarya above) and the -p param as XET_USER_NAME
   and XET_USER_TOKEN environment variables. Also, for your python session, `pyxet.login()` will set the environment
   variables for you.

```sh
# Note: set this environment variable into your shell config (ex. .zshrc) so not lost.
export XET_USER_NAME=<YOUR XETHUB USERNAME>
export XET_USER_TOKEN=<YOUR PERSONAL ACCESS TOKEN PASSWORD>
```

## Blob store tooling

pyxet also provides a python SDK (CLI is on the way!)  for interacting with XetHub blob stores.

* A URI for pyxet is `<username>/<repository>/<branch>/<path to whatever>`
* `pyxet.XetFs` implement [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)

```python
import pyxet

fs = pyxet.XetFS()  # fsspec filesystem

# Reads
fs.info(
    "xdssio/titanic/main/titanic.csv")  # {'name': 'https://xethub.com/main/titanic.csv', 'size': 61194, 'type': 'file'}
fs.open("xdssio/titanic/main/titanic.csv", 'r').read(11)  # 'PassengerId'
fs.get("xdssio/titanic/main/data/*parquet", "data", recursive=True)  # Download file/directories recursively
fs.cp("xdssio/titanic/main/titanic.csv", "titanic.csv")  # fsspec cp
fs.ls("xdssio/titanic/main/data/", detail=False)  # ['data/titanic_0.parquet', 'data/titanic_1.parquet']

# Writes - You need to have write permissions to that repo
with fs.transaction("xdssio/titanic/main"):
    fs.cp("xdssio/titanic/main/titanic.csv", "xdssio/titanic/main/titanic2.csv")
fs.info("xdssio/titanic/main/titanic2.csv")
with fs.transaction("xdssio/titanic/main"):
    fs.rm("xdssio/titanic/main/titanic2.csv")
fs.info("xdssio/titanic/main/titanic2.csv")  # FileNotFoundError: xdssio / titanic / main / titanic2.csv
```
