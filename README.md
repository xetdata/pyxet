---

### :construction: :construction: :construction: _pyxet is new and under active development. See details below._ :construction: :construction: :construction:

---

<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/0c7608c97f6a2a0cb2c83dd38fb717913c4d7522/docs/images/logo.png" alt="logo" width="400" />
</p>

# pyxet - The SDK for XetHub

[![Version](https://img.shields.io/pypi/v/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Python](https://img.shields.io/pypi/pyversions/pyxet.svg?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![License](https://img.shields.io/github/license/xetdata/pyxet?style=flat)](https://github.com/xetdata/pyxet/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/pyxet?style=flat)](https://pypi.python.org/pypi/pyxet/)
[![Documentation Status](https://readthedocs.org/projects/pyxet/badge/?version=latest)](https://pyxet.readthedocs.io/en/latest/?badge=latest)
[![Discord](https://img.shields.io/discord/1100889165777862807)](https://discord.gg/KCzmjDaDdC)

### Note: This project is just getting started. Please join our [Discord server](https://discord.gg/KCzmjDaDdC) to get involved. To stay informed about updates please star this repo and sign up for [XetHub](https://xethub.com/user/sign_up) to get the newsletter.

## What is it?

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.

## Preliminary Features (more to come, get involved!)

1. A filesystem interface:
    * [fsspec](https://filesystem-spec.readthedocs.io)
        * copy
        * list
        * etc.
    * [glob](https://docs.python.org/3/library/glob.html)
    * [pathlib.Path](https://docs.python.org/3/library/pathlib.html)(WIP)

2. Integrations:
    - [x] [GitHub](https://github.com) [submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
    - [x] [pandas](https://pandas.pydata.org)
    - [x] [polars](https://pola-rs.github.io/polars-book/)
    - [x] [pyarrow](https://arrow.apache.org/docs/python/)
    - [ ] [duckdb](https://duckdb.org/)
    - [ ] [dask](https://dask.org/)
    - [ ] [ray](https://ray.io/)

## Documentation

For API documentation and full examples, please see [here](https://pyxet.readthedocs.io/en/latest/).

## Getting Started

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

### Blob store tooling

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

### ML Demo

A slightly more complete demo doing some basic ML is as simple as setting up your virtualenv with:

```sh
pip install scikit-learn ipython pandas
```

* Make sure to set your XET_USERNAME and XET_TOKEN environment variables, or run: `pyxet.login('username', 'token')`

```python
import pyxet
import json
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

df = pd.read_csv("xet://xdssio/titanic.git/main/titanic.csv")  # read data from XetHub
### Standard ML workflow ###
target_names, features, target = ['die', 'survive'], ["Pclass", "SibSp", "Parch"], "Survived"

test_size, random_state = 0.2, 42
train, test = train_test_split(df, test_size=test_size, random_state=random_state)
model = RandomForestClassifier().fit(train[features], train[target])
predictions = model.predict(test[features])
print(classification_report(test[target], predictions, target_names=target_names))

# Any parameters we want to save
info = classification_report(test[target], predictions,
                             target_names=target_names,
                             output_dict=True)
info["test_size"] = test_size
info["random_state"] = random_state
info['features'] = features
info['target'] = target

results = pd.DataFrame([{'accuracy': info['accuracy'],
                         'precision': info['macro avg']['precision'],
                         'recall': info['macro avg']['recall']}])

### persist model and metrics to XetHub ###
# Assuming the branch exists, we can write to it the model and the metrics
fs = pyxet.XetFS()
with fs.transaction("xdssio/titanic/experiment-1/"):
    fs.mkdirs("xdssio/titanic/experiment-1/metrics", exist_ok=True)
    fs.mkdirs("xdssio/titanic/experiment-1/models", exist_ok=True)
    results.to_csv(fs.open("xdssio/titanic/experiment-2/metrics/results.csv", "w"), index=False)  # write results
    pickle.dump(model, fs.open("xdssio/titanic/experiment-1/models/model.pickle", 'wb'))  # save model
    json.dump(info, fs.open("xdssio/titanic/experiment-1/metrics/info.json", 'w'))  # any other metadata

# Load model in an inference server
import pyxet
import pickle

model = pickle.load(fs.open("xdssio/titanic/experiment-1/models/model.pickle", 'rb'))  # RandomForestClassifier()

# Compare results across branches
import pyxet
import pandas as pd

dfs = []
for branch in ['experiment-1', 'experiment-2']:
    df = pd.read_csv(f"xet://xdssio/titanic.git/{branch}/metrics/results.csv")
    df['branch'] = branch
    dfs.append(df)
pd.concat(dfs)

"""
   accuracy  precision    recall        branch
0  0.731844   0.724591  0.715573  experiment-1
0  0.631844   0.724591  0.715573  experiment-2
"""
```

## Contributing & Getting Help

This project is just getting started. We were so eager to get pyxet out that we have not gotten all the code over to
this repository yet. We will bring the code here very soon. We fully intend to develop this package in public under the
BSD license.

In the coming days we will add a roadmap to make it easier to know when pyxet features are being implemented and how you
can help.

For now, join our [Discord server](https://discord.gg/KCzmjDaDdC) to talk with us. We have ambitious plans and some very
useful features under development / partially working (ex. write back to XetHub repos, easy commit messages, stream
repositories locally, easily load the same file across Git branches, and more).


