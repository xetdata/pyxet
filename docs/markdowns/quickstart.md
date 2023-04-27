# Quickstart

[XetHub](https://xethub.com/) is a cloud storage with git capabilities. It is a great place to store your data, models,
logs and code.    
This library allows you to access XetHub from Python.

## Installation

1. [Create an account or sign in](https://xethub.com)
2. Get a personal access token [here](https://xethub.com/user/settings/pat) and set it `XET_USER`, `XET_TOKEN` environment
   variables.
3. Install the library

`pip install pyxet`

## Usage

We'll start with a simple machine learning example of the [titanic dataset](https://www.kaggle.com/c/titanic).

```python
import pyxet

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# make sure to set your XET_USER and XET_TOKEN environment variables, or run:
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

What do we care about? We care about the model, the data, the metrics and the code.

### Setup

Let's [create a new repo](https://xethub.com/xet/create) in the UI or programmatically:

We clone the repo to our local filesystem, saving everything we want, and committing it:

```bash
git xet clone https://xethub.com/user/repo
```

```python
import pyxet
import json
import joblib


df.to_csv(f"titanic.csv",
          index=False)

with open("info.json") as f:
    json.dump(info, f)

with open("model.pkl") as f:
    joblib.dump(model, f)
```
```bash
git add .
git commit -m "first commit"
git push
```

Of course you can save your code as well, and upload it with the command:
> This will work no matter the size of your data, model or logs.

## Next steps

Do you want to experiment with another model?   
you can clone the repo, create a new branch and try a different model.

* All models will be saved, managed and versioned using git.
* All metrics and logs will be saved such that you can compare them easily.
* You can share your repo with your team and collaborate on it.
    * Sharing data
    * Pushing code
    * Running experiments
    * Saving models
    * Saving logs

Checkout this [titanic app](https://xethub.com/xdssio/titanic-server-example), for a more comprehensive example.



