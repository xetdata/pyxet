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

## Usage

XetHub lets you store up to 1TB of files in a single repository. With pyxet, you can access these files easily using familiar file system operations. 
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

## Advanced ML example

Start this demo by setting up your virtualenv with:

```sh
pip install scikit-learn ipython pandas
```

Now use this code to generate some parameters.

```sh
import pyxet

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# make sure to set your XET_USER_NAME and XET_USER_TOKEN environment variables, or run:
# pyxet.login('username', 'token')

df = pd.read_csv("xet://xdssio/titanic.git/main/titanic.csv")  # read data from XetHub
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
```

Continue to the next section to see how you can use pyxet with git-xet on a private XetHub repository.

