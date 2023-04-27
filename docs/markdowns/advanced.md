# Advanced Usage with XetHub 

Working with private data that you don't want to share? Sign up for a XetHub account to use pyxet with your private repositories of up to 100TB. 

## Install and create a new repo

1. Sign up for [XetHub](https://xethub.com/user/sign_up)
2. Install the [git-xet client](https://xethub.com/explore/install) and create a token
3. Copy and execute the login command: `git xet login -u <username> -e <email> -p **********`
4. To make these credentials available to pyxet, set the username and email parameters as XET_USERNAME and XET_TOKEN environment variables. 
In your python session, pyxet.login() will set the environment variables for you.

```sh
# Note: preserve these environment variables by adding to your shell config (ex. .zshrc) 
export XET_USERNAME=<YOUR XETHUB USERNAME>
export XET_TOKEN=<YOUR PERSONAL ACCESS TOKEN PASSWORD>
```
5. [Create a new private repository](https://xethub.com/xet/create) through the UI and call it MLDemo 
6. Clone your new repository locally with `git xet clone <repo URL>`

## ML training example

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

# make sure to set your XET_USERNAME and XET_TOKEN environment variables, or run:
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

To save your outputs:

```sh
import json
import joblib

df.to_csv(f"titanic.csv",
          index=False)

with open("info.json") as f:
    json.dump(info, f)

with open("model.pkl") as f:
    joblib.dump(model, f)
```

Push anything you worked with to your private repository with normal Git commands.

```sh
git add .
git commit -m "first commit"
git push
```

## Next steps

Do you want to experiment with another model? Clone the repo, create a new branch, and try a different model.

All models will be saved, managed, and versioned with Git, and all metrics and logs will be saved such that you can compare them easily.
You can [share your repo](https://xethub.com/assets/docs/workflows/invite-collaborators) with your teammates and collaborate on the results.

Check out this [titanic app](https://xethub.com/xdssio/titanic-server-example) for a more comprehensive example of a ML project in development.

