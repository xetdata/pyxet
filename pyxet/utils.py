import subprocess


def shell(commnad, shell=True, stdout=subprocess.PIPE, encoding="utf-8", verbose=False):
    if verbose:
        print(commnad)
    ret = subprocess.run(commnad, shell=shell, stdout=stdout).stdout
    return ret.decode(encoding) if ret else None