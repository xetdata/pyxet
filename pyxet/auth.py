import os
from pyxet.utils import shell


def login(username: str = None, password: str = None, email: str = None, force: bool = False):
    username = username or os.getenv("XET_USERNAME")
    password = password or os.getenv("XET_PASSWORD")
    email = email or os.getenv("XET_EMAIL")
    command = f"git xet login -e {email} -u {username} -p {password}"
    if force:
        command += " --force"
    return shell(command)
