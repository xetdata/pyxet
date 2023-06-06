# File system

Pyxet implements a simple and intuitive API based on the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library.
Use the same API to access local files, remote files, and files in XetHub. All operations are currently read-only; write functionality 
is in development.

## Using URLs

Xet URLs should be of the form `xet://<repo_user>/<repo_name>/<branch>/<path-to-file>`, where `<path-to-file>` is optional if the URL 
refers to a repository. The xet:// prefix is inferred as needed, or if the URL is given as https://.  

Setting a user and token is required for private repositories. They may be provided as explicit arguments to most pyxet functions, 
or they can be passed in with the URL by prefixing `xet://<user>[:token]@xethub.com/`. For example, 
`xet://user1:mytokenxyz@xethub.com/data_user/data_repo/main/data/survey.csv` would access the file `data/survey.csv` on 
the branch `main` of the repo `data_user/data_repo`  with credentials `user=user1` and `token=mytokenxyz`. 

For example, to refer to the results.csv file in the main branch of the XetHub Flickr30k repo, the following work: 
- `xet://xethub.com/XetHub/Flickr30k/main/results.csv` (all fsspec compatible packages)
- `/XetHub/Flickr30k/main/results.csv` (pyxet.open) 
- `https://xethub.com/XetHub/Flickr30k/main/results.csv` (pyxet.open) 

## pyxet.open

To open a file from an XetHub repository, you can use the `pyxet.open()` function, which takes a file URL in the format 
`xet://<repo_user>/<repo_name>/<branch>/<path-to-file>`.

Example usage of `pyxet.open`:
```sh
  import pyxet

  # Open a file from a public repository.
  f = pyxet.open('xet://xethub.com/XetHub/Flickr30k/main/results.csv')

  # Read the contents of the file.
  contents = f.read()
  f.close()
```



