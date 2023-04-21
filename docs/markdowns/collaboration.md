# Collaboration

One of the best aspects of Xet is the ability to collaborate with others.

A standard machine learning solution architecture would be something like this:
<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/main/docs/images/standard.png?raw=true" alt="logo" width="1000" />
</p>   

* Every team-member would have to know the addresses of all the relevant S3 buckets, and the credentials to access them.
* Different versions of models would be saved in different files with many replicates, and dev and prod models would
  probably be managed separately.
* Monitoring is often done in another bucket, and the data would be copied to a different bucket or database for
  analysis.
* Training data will be append-only, and cleaning and ETL would be firectories in buckets and many data copies.
* For ML Experiments, another bucket, and as best practice, each would have a snapshot of the data somewhere for
  reproducibility.
* Since serving code depends greatly on the model and technologies, the data-scientist and mlops engineer would have
  friction to overcome at every code change.
* When the data distribution is changed or model assumptions, or any other data related change, more friction is
  introduced.

Can we do better?
<p align="center">
   <img src="https://github.com/xetdata/pyxet/blob/main/docs/images/xethub.png?raw=true" alt="logo" width="1000" />
</p>   
We can use XetHub to share data, models, and code, with a simple natural distinction view:

* Addresses of things are as directories and files.
* Versions are managed with git instead of Addresses.

This let a whole team collaborate on a single project, and share data, models, and code, without friction.
Everyone can post issues with link to code, revert models and even revert data issues.

One of the easiest way to look at it, is that at any given branch, there is a single model file. prod, dev or
experiment, the entire app works the same without any manged addresses.

We have a simple example of this in the [XetHub Demo]() repo.




