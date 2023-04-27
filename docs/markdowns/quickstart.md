# Quick Start

[XetHub](https://xethub.com/) is a cloud storage platform with Git capabilities. It is a great place to store your data, models,
logs, and code. The pyxet library allows you to easily access XetHub from Python.

## Installation

Assuming you are on a supported OS (MacOS or Linux) and are using a supported version of Python (3.7+), set up your virtualenv with:

```sh
$ python -m venv .venv
...
$ . .venv/bin/activate
```

Then, install pyxet with:

```sh
$ pip install pyxet
```

After installing pyxet, the next step is to confirm your git configuration is complete.

Note: This requirement will be removed soon, but today git user.email and git user.name are required to be set in order to use pyxet. This is because XetHub is built on scalable Git repositories, and pyxet is built with libgit, and libgit requires git user configuration to be set in order to work.

```sh
git config --global user.name "Your Name"
git config --global user.email "your_email_address@email.com"
```

## Usage

XetHub lets you store up to 100TB of files in a single repository. With pyxet, you can access these files easily. 
To verify that pyxet is working, let's load a CSV file directly into a Pandas dataframe, leveraging pyxet's support for Python fsspec.

```sh
# assumes you have already done pip install pandas
import pandas as pd
import pyxet

df = pd.read_csv('xet://xdssio/titanic/main/titanic.csv')
df
```

This will return something like:

```sh
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

Now you can work directly with files without needing to download the full repository.

Continue to see how you can use pyxet on a private XetHub repository.

