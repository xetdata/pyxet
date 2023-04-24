# Model versioning

Use-cases:

* A/B testing between branches.
* Update a model in production is as easy as merging it.
* We can mount the models folder or load it explicitly.

## Manage with git

Currently, many organisations manage their experiments by saving snapshot of the data, the logs, the metrics and the
models.    
Best models are copied to a different locations to get into dev and production environments. Sometimes managed by a
database, or with docker-image registry.        
Often enough, another third-party tool is used to manage the experiments - which then needs to be integrated with the
rest of the development stack.

*An example:*

```bash
s3://project-data/
├── data/
│ ├── snapshot-210322.csv
│ ├── snapshot-210323.csv

s3://project-models/
├── v1/
│ ├── model-210322.pkl
│ ├── model-210323.pkl
├── prod/
│ ├── model.pkl
├── dev/
│ ├── model.pkl
├── a-b-test-210322/
│ ├── model.pkl
├── a-b-test-210323/
│ ├── model.pkl

s3://project-metrics/ (accuracy, etc.)
├── v1/
│ ├── 210322.json
│ ├── 210323.json

s3://project-logs/ (bugs, errors, etc.)
├── v1/
│ ├── 210322.log
│ ├── 210323.log

s3://model-monitoring/ (model drift, etc.)
├── prod/
│ ├── 210322.csv
│ ├── 210323.csv
├── dev/
│ ├── 210322.csv
│ ├── 210323.csv
├── a-b-test
│ ├── 210322.csv
│ ├── 210323.csv

https://github.com/org/project-inference
├── app.py
├── dockerfile

https://github.com/org/project-training
├── train.py
├── notebooks/
│ ├── 210322.ipynb
│ ├── 210323.ipynb

https://github.com/org/project-ops
├── docker-compose.yml
├── teraform.tf

...
```

And that not including sharing the data or models with other teams.

With XetHub, we can use git to manage the experiments and models together with the code.
Optionally, we can use [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) to manage the data.

```bash
xet://org/project (branch-prod/dev/ab-test-210322/ab-test-210323)
├── data/ xet://org/project/data (submodule)
│   ├── data.csv
├── models/
│   ├── model.pkl
├── metrics/
│   ├── model.json
├── logs/
│   ├── app.log
├── monitoring/
│   ├── predictions.csv
│   ├── drift.csv
├── src (Always fit the right model and technologies)
│   ├── train.py
│   ├── serve.py 
```

It means that we can save a single model (or a whole pipeline) per branch - and merge to the environment of our
choosing will merge the model as well.
Logs of bugs, drift etc. are always fitting the model in production and we can always reproduce the results.

### Experiment with some feature engineering

Checkout a new branch, add the feature engineering, train the model and commit the new model, logs and metrics.   
Good enough to go to production? Merge it all to prod in a single step.

- [ ] [Example (WIP)]()

### Reproduce a model

We can always reproduce the results, and compare the models by checking out the branch and re-running.

- [ ] [Example (WIP)]()

### Re-raining with more data?

We can simply checkout from prod for example to a new experiment branch, pull the new data
with `git submodule update data` and run the training again.   
We will override the model, the metrics, the model-checkpoints etc. and we can merge them back to prod if we want.  
This way, the model in prod is always up-to-date with it's correct metrics, inference code and relevant logs.

Everything **this** model needs is saved in the repo. If changes to the app are needed, they are managed together.

- [ ] [Example (WIP)]()

### A/B testing [WIP]

We add a submodule *experiments* to the monitoring folder, and we can save the results of the inference there.
We now create a new branch *A* and *B* for each experiment, each saves it's own model, metrics, logs and monitoring, and
deploy them.

We can later compare the results.

```python
import pyxet
import pandas as pd

branches = pyxet.ls("xet://org/project/**/monitoring/experiments/results.csv")
results = []
for branch in branches():
    df = pd.read_csv(f"xet://org/project/{branch}/monitoring/serving/results.csv")
    df['branch'] = branch
    results.append(df)
results = pd.concat(results)
# Analyze the results
```

- [ ] [Example (WIP)]()

## Saving/Loading a model remotely

```python
import pyxet

fs = pyxet.repo("xet://user/repo/branch")

# pickle/cloudpickle
import pickle

pickle.dump(model, fs.open('model.pickle', 'wb'))

loaded_model = pickle.load(fs.open('model.pickle', 'rb'))

# Joblib
import joblib

with fs.open('model.joblib', 'wb') as f:
    joblib.dump(model, f)

with fs.open('model.joblib', 'rb') as f:
    model = joblib.load(f)

# Any model in bytes
import io
import torch

buffer = io.BytesIO()
torch.save(model, buffer)
with fs.open('model.pt', 'wb') as f:
    f.write(buffer.getvalue())

# This also works for directories
import mlflow.sklearn

mlflow.sklearn.save_model(model, "models/model")
"""
models/model/
        ├── MLmodel
        ├── model.pkl
        ├── conda.yaml
        ├── python_env.yaml
        └── requirements.txt
"""
# Or we can use git
repo = pyxet.repo("xet://user/repo/branch").clone('.')
model.save('models/model')
repo.git.add_commit_push('models/model', 'Save model')
```

With the CLI

```bash
pyxet copy model.joblib xet://user/repo/branch/model.joblib
```




