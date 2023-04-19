# CLI

The file system APIs are the most straight forward. They are based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library.   
* [Copy conventions](https://filesystem-spec.readthedocs.io/en/latest/copying.html)

```bash
xet login -e email -u username -p password -i id_rsa
xet cp -r data/* et@xethub.com:xdssio/repo.get/branch/data
xet mv -r data/* et@xethub.com:xdssio/repo.get/branch/data
xet rm -r https://xet@xethub.com:xdssio/repo.get/branch/data
xet upload -r file.txt et@xethub.com:xdssio/repo.get/branch/<automatically figure out file.txt>
xet s3 cp -r s3:/my-bucket/data/* https://xet@xethub.com:xdssio/repo.get/branch/data
xet gs cp -r gs:/my-bucket/file.txt https://xet@xethub.com:xdssio/repo.get/branch/file.txt
xet az cp -r gs:/my-bucket/data/ https://xet@xethub.com:xdssio/repo.get/branch/data

xet download -r https://xet@xethub.com:xdssio/repo.get/branch/data
xet login -u xdssio -e jonathan@xdss.io -p ZwAHK0Dq9Nqqt4i3WOJXjw -i <path to ssh file>
xet clone --lazy <repo> --branch <branch>
xet clone --materialize <repo> 

```