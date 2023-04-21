# Model versioning

In case we use many models, we can use git to manage the versions.
We have an endpoint which loads a model from a repo + branch.
Use-cases:

* A/B testing between branches.
* Update a model in production is as easy as merging it.
* We can mount the models folder or load it explicitly.

Examples:

* [ ] [FastAPI]()
* [ ] [Modal.com]()
* [ ] [Sagemaker]()

### Saving/Loading a model remotely

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

# Mount for special cases - like an output folder for MLflow
import mlflow.sklearn

fs.mount('models', 'wb')
mlflow.sklearn.save_model(model, "models/model")
"""
models/model/
        ├── MLmodel
        ├── model.pkl
        ├── conda.yaml
        ├── python_env.yaml
        └── requirements.txt
"""

fs.mount('models', 'r')
model = mlflow.sklearn.load_model.load_model('model')
```

With the CLI

```bash
pyxet copy model.joblib xet://user/repo/branch/model.joblib
```

## Examples
### Using a mounted repo

* [titanic-example](https://xethub.com/xdssio/titanic-server-example)

```bash
git xet mount https://xethub.com/xdssio/titanic-server-example.git server
# pip install -r server/requirements.txt # <-- if needed
uvicorn server.src.serve:app --reload
# Checkout http://127.0.0.1:8000/docs or run: 
curl -X 'POST' \
  'http://127.0.0.1:8000/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "PassengerId": 1,
  "Pclass": 3,
  "Name": "Braund, Mr. Owen Harris",
  "Sex": "male",
  "Age": 22,
  "SibSp": 1,
  "Parch": 0,
  "Ticket": "A/5 21171",
  "Fare": 7.25,
  "Embarked": "S"
}'
umount server
```


