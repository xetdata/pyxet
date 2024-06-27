#!/usr/bin/env python

# Pull in everything from pyxet, without the relative imports. 
from pyxet.cli import cli

# Package in s3 dependencies, otherwise these 
# will just give other repo errors.  
import s3fs
import boto3
import botocore

if __name__ == "__main__":
    cli()
