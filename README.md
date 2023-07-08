---

### :construction: :construction: pyxet is new and under active development :construction: :construction:

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

## What is it?

pyxet is a Python library that provides a lightweight interface for the [XetHub](https://xethub.com/) platform.

This project is just getting started and we have not moved all our code over to this repository yet. We intend to develop this package in public under the BSD license.

| Version     | Estimated Release Date | Updates|
| ------------|------------------------|--------|
| pyxet 0.0.8 | 7/12/2023	             | pyxet and xet-core codebases are open source! <br/> Experimental support for >10TB repositories <br/>Windows support <br/>XetHub moves to an open-core software model |
| pyxet 0.1   | 7/27/2023              | Code of Conduct published, contributions welcome!  <br/>Production support for >10TB repositories |

Join our [Discord](https://discord.gg/KCzmjDaDdC) to get involved. To stay informed about updates, star this repo and sign up for [XetHub](https://xethub.com/user/sign_up) to get the newsletter.

## Preliminary Features

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

## Installation

Assuming you are on a supported OS (MacOS or Linux) and are using a supported version of Python (3.7+), set up your
virtualenv with:

```sh
$ python -m venv .venv
$ . .venv/bin/activate
```

Then, install pyxet with:

```sh
$ pip install pyxet
```

## Demo

To verify that pyxet is working, let's load a CSV file directly into a Pandas dataframe, leveraging pyxet's support for
Python fsspec.

```python
import pyxet            # make xet:// protocol available
import pandas as pd     # assumes pip install pandas has been run

df = pd.read_csv('xet://xdssio/titanic/main/titanic.csv')
df
```

This should return something like:

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

## Working with a Blob Store

pyxet provides a Python SDK (with a CLI on the way!) for interacting with XetHub repositories as blob stores, while
leveraging the power of Git branches and versioning.

A XetHub URL for pyxet is in the form:
```
xet://<repo_owner>/<repo_name>/<branch>/<path_to_file>
```

Unlike with traditional blob stores, the ability to call a branch means that you can choose whether to
use the most recent version of a file/directory or to reference a particular branch or commit.

To work with a repository as a file system, use `pyxet.XetFS`, which implements [fsspec](https://filesystem-spec.readthedocs.io/en/latest/)
Here are some simple ways to access information from an existing repository:

```python
import pyxet

fs = pyxet.XetFS()  # fsspec filesystem

fs.info("xdssio/titanic/main/titanic.csv")
# returns repo level info: {'name': 'https://xethub.com/xdssio/titanic/titanic.csv', 'size': 61194, 'type': 'file'}

fs.open("xdssio/titanic/main/titanic.csv", 'r').read(20)
# returns first 20 characters: 'PassengerId,Survived'

fs.get("xdssio/titanic/main/data/", "data", recursive=True)
# download remote directory recursively into a local data folder

fs.ls("xdssio/titanic/main/data/", detail=False)
# returns ['data/titanic_0.parquet', 'data/titanic_1.parquet']
```

Pyxet also allows you to write to repositories with Git versioning.

Writing files with pyxet
========================

## Create an account, install git-xet

To use pyxet on your own XetHub repository, or to write back to an existing repository, set up an account.
Then install git-xet, a Git extension, to seamlessly manage your XetHub repositories.

1. Sign up for [XetHub](https://xethub.com/user/sign_up)
2. Install the [git-xet client](https://xethub.com/explore/install) and create a token
3. Copy and execute the login command:
   ```sh
   $ git xet login -u <username> -e <email> -p **********
   ```
4. To make these credentials available to pyxet, set the username and token parameters as XET_USER_NAME and XET_USER_TOKEN environment variables.
   ```sh
   # Save these environment variables to your shell config (ex. .zshrc)
   export XET_USER_NAME=<YOUR XETHUB USER NAME>
   export XET_USER_TOKEN=<YOUR PERSONAL ACCESS TOKEN>
   ```
   You can also manually log in to pyxet from Python with `pyxet.login('user_name', 'token')`.

Now that you have an account, you can contribute to repositories that you have access to.

## Create your own Titanic repository

Let's walk through a more complete demo of how to use pyxet for some basic ML.

Use the XetHub UI to [create a new repository](https://xethub.com/xet/create). Name the repository `titanic`,
clone the empty repository to your local machine, then create a branch named `experiment-1`.

```sh
cd titanic
git checkout -b experiment-1 && git push -u origin experiment-1
```

Start a new virtualenv and install some dependencies:

```sh
$ python -m venv .venv
$ . .venv/bin/activate
$ pip install pyxet scikit-learn ipython pandas
```

From your `experiment-1` branch, train and evaluate:
```python
import pyxet
import json
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

df = pd.read_csv("xet://xdssio/titanic/main/titanic.csv")  # read data from XetHub

# Standard ML workflow
target_names, features, target = ['die', 'survive'], ["Pclass", "SibSp", "Parch"], "Survived"

test_size, random_state = 0.2, 42
train, test = train_test_split(df, test_size=test_size, random_state=random_state)
model = RandomForestClassifier().fit(train[features], train[target])
predictions = model.predict(test[features])
print(classification_report(test[target], predictions, target_names=target_names))

# Save important parameters
info = classification_report(test[target], predictions,
                             target_names=target_names,
                             output_dict=True)
info["test_size"] = test_size
info["random_state"] = random_state
info['features'] = features
info['target'] = target

# Record metrics for comparison
results = pd.DataFrame([{'accuracy': info['accuracy'],
                         'precision': info['macro avg']['precision'],
                         'recall': info['macro avg']['recall']}])
```

### Writing back to XetHub

After training your model, you can persist both the model and metrics back to XetHub.
Update the `<user_name>` fields below and run:

```python
fs = pyxet.XetFS()
with fs.transaction as tr:
    tr.set_commit_message("Write experiment 1 results back to repo")
    fs.mkdirs("<user_name>/titanic/experiment-1/metrics", exist_ok=True)
    fs.mkdirs("<user_name>/titanic/experiment-1/models", exist_ok=True)
    results.to_csv(fs.open("<user_name>/titanic/experiment-1/metrics/results.csv", "w"), index=False)  # write results
    pickle.dump(model, fs.open("<user_name>/titanic/experiment-1/models/model.pickle", 'wb'))  # save model
    json.dump(info, fs.open("<user_name>/titanic/experiment-1/metrics/info.json", 'w'))  # any other metadata
```

If you navigate to your titanic repository on XetHub, you'll see the new files show up
with the corresponding commit in your `experiment-1` branch.

### Loading models

You can easily load a XetHub model from an inference server:

```python
import pyxet
import pickle
model = pickle.load(fs.open("<user_name>/titanic/experiment-1/models/model.pickle", 'rb'))
```

### Comparing across branches

Versioned experiments on branches enables easy comparison.
To try this out, create a new `experiment-2` branch:
```sh
git checkout -b experiment-2 && git push -u origin experiment-2
```

Run the same code as above, but change the `test_size` and `random_state` values. This time, persist
your model and metrics back to XetHub in the `experiment-2` branch.

```python
fs = pyxet.XetFS()
with fs.transaction as tr:
    tr.set_commit_message("Write experiment 2 results back to repo")
    fs.mkdirs("<user_name>/titanic/experiment-2/metrics", exist_ok=True)
    fs.mkdirs("<user_name>/titanic/experiment-2/models", exist_ok=True)
    results.to_csv(fs.open("<user_name>/titanic/experiment-2/metrics/results.csv", "w"), index=False)  # write results
    pickle.dump(model, fs.open("<user_name>/titanic/experiment-2/models/model.pickle", 'wb'))  # save model
    json.dump(info, fs.open("<user_name>/titanic/experiment-2/metrics/info.json", 'w'))  # any other metadata
```

Compare your results, making sure to update `<user_name>` in the code below:

```python
import pyxet
import pandas as pd

dfs = []
for branch in ['experiment-1', 'experiment-2']:
    df = pd.read_csv(f"xet://<user_name>/titanic/{branch}/metrics/results.csv")
    df['branch'] = branch
    dfs.append(df)
pd.concat(dfs)
```

Changing `test_size` and `random_state` to 0.5 and 30 respectively results in the following comparison printout:

```sh
   accuracy  precision    recall        branch
0  0.731844   0.724591  0.715573  experiment-1
0  0.688341   0.673824  0.653577  experiment-2
```
