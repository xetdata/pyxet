"""
Provides URL parsing for Xet Repos
"""
import unittest
from urllib.parse import urlparse
import sys
import os

has_warned_user_on_url_format = False

__default_endpoint = None

def set_default_endpoint(endpoint): 
    global __default_endpoint
    if __default_endpoint is None:
        __default_endpoint = normalize_endpoint(endpoint) 

def get_default_endpoint():
    global __default_endpoint
    if __default_endpoint is not None:
        endpoint = __default_endpoint
    elif "XET_ENDPOINT" in os.environ:
        env_endpoint = os.environ["XET_ENDPOINT"]
        endpoint = __default_endpoint = env_endpoint
    else:
        sys.stderr.write("\nWarning:  Endpoint defaulting to xethub.com; use URLs of the form \n"
                            "          xet://<endpoint>:<user>/<repo>/<branch>/<path>.\n")
        endpoint = __default_endpoint = "xethub.com"

    return endpoint 


def normalize_endpoint(endpoint = None):
    global __default_endpoint
    if endpoint is None:
        return get_default_endpoint()

    # support default_endpoint with a scheme (http/https)
    if endpoint is not None:
        endpoint_split = endpoint.split('://')
        if len(endpoint_split) == 1:
            endpoint = endpoint_split[0]
        elif len(endpoint_split) == 2:
            endpoint = endpoint_split[1]
        else:
            raise ValueError(f"Domain {endpoint} not valid url.")

    return endpoint


class XetPathInfo:
    __slots__ = ['scheme', 'endpoint', 'user', 'repo', 'branch', 'path', 'endpoint_explicit']

    def _repo_branch_path(self):
        return "/".join(s for s in [self.repo, self.branch, self.path] if s)

    def url(self):
        return f"{self.scheme}://{self.endpoint}:{self.user}/{self._repo_branch_path()}"

    def base_path(self): 
        """
        Returns the base user/repo/branch  
        """ 
        if self.endpoint_explicit:
            return f"{self.endpoint}:{self.user}/{self.repo}/{self.branch}"
        else:
            return f"{self.user}/{self.repo}/{self.branch}"


    def remote(self, endpoint_only = False):
        """
        Returns the endpoint of this in the qualified user[:token]@endpoint
        """
        if endpoint_only:
            ret = f"https://{self.endpoint}/"
        elif self.repo:
            ret = f"https://{self.endpoint}/{self.user}/{self.repo}"
        else:
            ret = f"https://{self.endpoint}/{self.user}"

        # This should work but has issues in xet-core
        #if branch and self.branch:
        #    ret = f"https://{self._user_at_endpoint()}/{self.repo}/{self.branch}"
        #elif self.repo:
        #    ret = f"https://{self._user_at_endpoint()}/{self.repo}"
        #else:
        #    ret = f"https://{self._user_at_endpoint()}"
        
        return ret
    
    def endpoint_url(self):
        """
        https://endpoint:user/
        """
        return f"https://{self.endpoint}" 

    def name(self):
        """
        Returns the prefix: user/repo/branch/path
        """
        return f"{self.user}/{self._repo_branch_path()}"

    def __eq__(self, other: object) -> bool:
        return (self.scheme == other.scheme
                and self.endpoint == other.endpoint
                and self.user == other.user
                and self.repo == other.repo
                and self.branch == other.branch
                and self.path == other.path)

    def __repr__(self):
        return self.url()


def parse_url(url, default_endpoint=None, expect_branch = None, expect_repo = True):
    """
    Parses a Xet URL of the form 
     - xet://user/repo/branch/[path]
     - /user/repo/branch/[path]

    Into a XetPathInfo which forms it as remote=https://[endpoint]/user/repo
    branch=[branch] and path=[path].

    branches with '/' are not supported.

    If partial_remote==True, allows [repo] to be optional. i.e. it will
    parse /user or xet://user
    """
    url_info = url.split("://")

    # assert default_endpoint is not None

    if len(url_info) == 1: 
        scheme = "xet"
        url_path = url_info[0]
    elif len(url_info) == 2:
        scheme, url_path = url_info
    else: 
        scheme = None  # Raise the ValueError. 

    if scheme not in ["xet", "http", "https"]: 
        # The other 
        raise ValueError(f"URL {url} not of the form xet://<endpoint>:<user>/<repo>/...")


    # Set this as a default below     
    ret = XetPathInfo()
    # Set what defaults we can
    ret.scheme = "xet"

    netloc_info = url_path.split("/", 1)

    if len(netloc_info) == 1:
        netloc = netloc_info[0]
        path = ""
    else:
        netloc, path = netloc_info

    # Handle the case where we are xet://user/repo. In which case the endpoint
    # parsed is not xethub.com and endpoint="user".
    # we rewrite the parse the handle this case early.
    if ":" not in netloc:
        
        global has_warned_user_on_url_format

        if default_endpoint is None and not has_warned_user_on_url_format:
            sys.stderr.write("Warning:  The use of the xet:// prefix without an endpoint is deprecated and will be disabled in the future.\n"
                             "          Please switch URLs to use the format xet://<endpoint>:<user>/<repo>/<branch>/<path>.\n"
                             "          Endpoint now defaulting to xethub.com.\n\n")
            has_warned_user_on_url_format = True
        
        default_endpoint = normalize_endpoint(default_endpoint) 

        # Test explicitly for the case where this is just xet://
        if netloc.endswith(".com"):  # Cheap way now to see if it's a website or not; we won't hit this with the new format.
            ret.endpoint = netloc
            path_to_parse = path
        else:
            ret.endpoint = default_endpoint 
            path_to_parse = f"{netloc}/{path}"
        ret.endpoint_explicit = False
        explicit_user = None
    else:
        endpoint_user = netloc.split(":")
        if len(endpoint_user) == 2:
            ret.endpoint, explicit_user  = endpoint_user
            path_to_parse = f"{path}"
            if not ret.endpoint:
                ret.endpoint = default_endpoint
        else: 
            raise ValueError(f"Cannot parse user and endpoint from {netloc}")
        
        ret.endpoint_explicit = True

    path_endswith_slash = path_to_parse.endswith("/")

    components = [] if explicit_user is None else [explicit_user]
    components += list([t for t in [t.strip() for t in path_to_parse.split('/')] if t])

    if len(components) == 0:
        raise ValueError(f"Invalid Xet URL format; user must be specified. Expecting xet://<endpoint>:<user>/[repo/[branch[/path]]], got {url}")
    
    if len(components) == 1 and expect_repo is True:
        raise ValueError(f"Invalid Xet URL format; user and repo must be specified. Expecting xet://<endpoint>:<user>/<repo>/[branch[/path]], got {url}")
    
    if len(components) > 1 and expect_repo is False:
        raise ValueError(f"Invalid Xet URL format for user; repo given.  Expecting xet://<endpoint>:<user>/, got {url}")
       
    if len(components) == 2 and expect_branch is True:
        raise ValueError(f"Invalid Xet URL format; user, repo, and branch must be specified for this operation. Expecting xet://<endpoint>:<user>/<repo>/<branch>[/path], got {url}")

    if len(components) > 2 and expect_branch is False:
        raise ValueError(f"Invalid Xet URL format for repo; branch given.  Expecting xet://<endpoint>:<user>/<repo>, got {url}")

    
    ret.user = components[0]

    if len(components) > 1:
        ret.repo = components[1]
    else:
        ret.repo = ""
    
    if len(components) > 2:
        ret.branch = components[2]
    else:
        ret.branch = ""

    if len(components) > 3:
        ret.path = "/".join(components[3:])
        if path_endswith_slash:
            ret.path = ret.path + "/"
    else:
        ret.path = ""

    return ret
