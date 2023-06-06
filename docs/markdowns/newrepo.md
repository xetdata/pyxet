Using pyxet with git-xet
========================

Want to use pyxet on your own XetHub repository? Set up git-xet to use XetHub for repositories of up to 1TB. XetHub is 
a great place to store models, data, and more all together.

1. Sign up for [XetHub](https://xethub.com/user/sign_up)
2. Install the [git-xet client](https://xethub.com/explore/install) and create a token
3. Copy and execute the login command: `git xet login -u <username> -e <email> -p **********`
4. To make these credentials available to pyxet, set the username and email parameters as XET_USER_NAME and XET_USER_TOKEN environment variables.
In your python session, pyxet.login() will set the environment variables for you.

```sh
# Save these environment variables to your shell config (ex. .zshrc)
export XET_USER_NAME=<YOUR XETHUB USER NAME>
export XET_USER_TOKEN=<YOUR PERSONAL ACCESS TOKEN PASSWORD>
```

## Create your repository

Use the XetHub UI to [create a new repository](https://xethub.com/xet/create) and clone the repository to your local machine.
Populate it with anything you want or [migrate existing files](https://xethub.com/assets/docs/category/migrating-to-xethub), and use normal Git commands to push to your repository.

```sh
git add .
git commit -m "first commit"
git push
```

Now you can use the pyxet API for read-only access your repository! 
Write functionality is currently in development.

## Next steps

Once you have a repository, experimenting is easy. Simply clone, create a branch, and try an approach, using Git to record your changes.
You can [share your repositories](https://xethub.com/assets/docs/workflows/invite-collaborators) with your teammates and use pull 
requests to collaborate.

Check out this [titanic app](https://xethub.com/xdssio/titanic-server-example) for a more comprehensive example of a ML project in development.

