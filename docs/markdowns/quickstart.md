# Quickstart

[XetHub](https://xethub.com/) is a cloud storage with git capabilities. It is a great place to store your data, models,
logs and code.    
This library allows you to access XetHub from Python.

## Installation

1. [Create an account or sign in](https://xethub.com) 
2. Get a personal access token [here](https://xethub.com/user/settings/pat) and set it `XETHUB_TOKEN` environment variable.
3. Install the library

`pip install pyxet`

## Usage

We'll start with a simple machine learning example of the [titanic dataset](https://www.kaggle.com/c/titanic).
```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

df = pd.read_csv("xet://xdssio/titanic.git/main/titanic.csv")  # read data from XetHub
features, target = ["Pclass", "SibSp", "Parch"], "Survived"

test_size, random_state = 0.2, 42
train, test = train_test_split(df, test_size=test_size, random_state=random_state)
model = RandomForestClassifier().fit(train[features], train[target])
predictions = model.predict(test[features])
print(classification_report(test[target], predictions, target_names=['die', 'survive']))
```

Let's create a new repo and save everything relevant to reproduce our model there. 

```python
import pyxet
import json
import joblib

username = "<your username>"
# Create a new repo
repo = pyxet.create(f"{username}/titanic-tutorial")

# save the data, the model and the info
df.to_csv(f"xet://{username}/titanic-tutorial.git/main/data/titanic.csv", index=False)  # save data to XetHubo

info = classification_report(test[target], predictions,
                             target_names=['die', 'survive'],
                             output_dict=True)
# Any other paremeters you want to save
info["test_size"] = test_size
info["random_state"] = random_state
info['features'] = features
info['target'] = target

with repo.open("info.json") as f:
    json.dump(info, f)

with repo.open("model.pkl") as f:
    joblib.dump(model, f)


```
Of course you can save your code as well, and upload it with the command:    
`xet cp <train.py> xet://<username>/titanic-tutorial.git/main/train.py`

You can also save your [FastAPI app](https://fastapi.tiangolo.com), checkpoints, logs directories, and even your [docker image](https://docs.docker.com/engine/reference/commandline/images/) to XetHub.
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

Have a look [here]() for more examples.


