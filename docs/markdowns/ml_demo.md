# ML Demo

A slightly more complete demo doing some basic ML is as simple as setting up your virtualenv with:

```sh
pip install scikit-learn ipython pandas
```

* Make sure to set your XET_USERNAME and XET_TOKEN environment variables, or run: `pyxet.login('username', 'token')`
* [Create a repo](https://xethub.com/xet/create) named `titanic` and create a branch named `experiment-1`.
    * `git checkout -b experiment-1 && git push`

```python
import pyxet
import json
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

df = pd.read_csv("xet://xdssio/titanic/main/titanic.csv")  # read data from XetHub

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

# Just important metrics to compare
results = pd.DataFrame([{'accuracy': info['accuracy'],
                         'precision': info['macro avg']['precision'],
                         'recall': info['macro avg']['recall']}])

### persist model and metrics to XetHub ###
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

# Compare results across branches (assuming you have a branch named experiment-2 too)
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