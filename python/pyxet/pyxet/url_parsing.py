"""
Provides URL parsing for Xet Repos
"""
import unittest
from urllib.parse import urlparse
import sys
import os

has_warned_user_on_url_format = False

__default_domain = None

def set_default_domain(domain): 
    global __default_domain
    if __default_domain is None:
        __default_domain = normalize_domain(domain) 

def normalize_domain(domain = None):
    global __default_domain
    if domain is None: 
        if __default_domain is not None:
            domain = __default_domain
        elif "XET_ENDPOINT" in os.environ:
            env_domain = os.environ["XET_ENDPOINT"]
            domain = __default_domain = env_domain
        else:
            sys.stderr.write("\nWarning:  Endpoint defaulting to xethub.com; use URLs of the form \n"
                             "          xet://<endpoint>:<user>/<repo>/<branch>/<path>.\n")
            domain = __default_domain = "xethub.com"

    # support default_domain with a scheme (http/https)
    if domain is not None:
        domain_split = domain.split('://')
        if len(domain_split) == 1:
            domain = domain_split[0]
        elif len(domain_split) == 2:
            domain = domain_split[1]
        else:
            raise ValueError(f"Domain {domain} not valid url.")

    return domain


class XetPathInfo:
    __slots__ = ['scheme', 'domain', 'user', 'repo', 'branch', 'path', 'domain_explicit']

    def _repo_branch_path(self):
        return "/".join(s for s in [self.repo, self.branch, self.path] if s)

    def url(self):
        return f"{self.scheme}://{self.domain}:{self.user}/{self._repo_branch_path()}"

    def base_path(self): 
        """
        Returns the base user/repo/branch  
        """ 
        if self.domain_explicit:
            return f"{self.domain}:{self.user}/{self.repo}/{self.branch}"
        else:
            return f"{self.user}/{self.repo}/{self.branch}"


    def remote(self):
        """
        Returns the endpoint of this in the qualified user[:token]@domain
        """

        if self.repo:
            ret = f"https://{self.domain}/{self.user}/{self.repo}"
        else:
            ret = f"https://{self.domain}/{self.user}"

        # This should work but has issues in xet-core
        #if branch and self.branch:
        #    ret = f"https://{self._user_at_domain()}/{self.repo}/{self.branch}"
        #elif self.repo:
        #    ret = f"https://{self._user_at_domain()}/{self.repo}"
        #else:
        #    ret = f"https://{self._user_at_domain()}"
        
        return ret
    
    def domain_url(self):
        """
        https://domain:user/
        """
        return f"https://{self.domain}/{self.user}" 

    def name(self):
        """
        Returns the prefix: user/repo/branch/path
        """
        return f"{self.user}/{self._repo_branch_path()}"

    def __eq__(self, other: object) -> bool:
        return (self.scheme == other.scheme
                and self.domain == other.domain
                and self.user == other.user
                and self.repo == other.repo
                and self.branch == other.branch
                and self.path == other.path)

    def __repr__(self):
        return self.url()


def parse_url(url, default_domain=None, expect_branch = None, expect_repo = True):
    """
    Parses a Xet URL of the form 
     - xet://user/repo/branch/[path]
     - /user/repo/branch/[path]

    Into a XetPathInfo which forms it as remote=https://[domain]/user/repo
    branch=[branch] and path=[path].

    branches with '/' are not supported.

    If partial_remote==True, allows [repo] to be optional. i.e. it will
    parse /user or xet://user
    """
    url_info = url.split("://")

    # assert default_domain is not None

    if len(url_info) == 1: 
        scheme = "xet"
        url_path = url_info[0]
    elif len(url_info) == 2:
        scheme, url_path = url_info
    else: 
        scheme = None  # Raise the ValueError. 

    if scheme not in ["xet", "http", "https"]: 
        # The other 
        raise ValueError(f"URL {url} not of the form xet://endpoint:user/repo/...")


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

    # Handle the case where we are xet://user/repo. In which case the domain
    # parsed is not xethub.com and domain="user".
    # we rewrite the parse the handle this case early.
    if ":" not in netloc:
        
        global has_warned_user_on_url_format

        if default_domain is None and not has_warned_user_on_url_format:
            sys.stderr.write("Warning:  The use of the xet:// prefix without an endpoint is deprecated and will be disabled in the future.\n"
                             "          Please switch URLs to use the format xet://<endpoint>:<user>/<repo>/<branch>/<path>.\n"
                             "          Endpoint now defaulting to xethub.com.\n\n")
            has_warned_user_on_url_format = True
        
        default_domain = normalize_domain(default_domain) 

        if netloc.endswith(".com"):  # Cheap way now to see if it's a website or not; we won't hit this with the new format.
            ret.domain = netloc
            path_to_parse = path
        else:
            ret.domain = "xethub.com" 
            path_to_parse = f"{netloc}/{path}"
        ret.domain_explicit = False
    else:
        domain_user = netloc.split(":")
        if len(domain_user) == 2:
            ret.domain, user  = domain_user
            path_to_parse = f"{user}/{path}"
        else: 
            raise ValueError(f"Cannot parse user and endpoint from {netloc}")
        
        ret.domain_explicit = True

    path_endswith_slash = path_to_parse.endswith("/")

    components = list([t for t in [t.strip() for t in path_to_parse.split('/')] if t])

    if len(components) == 0:
        raise ValueError(f"Invalid Xet URL format; user must be specified. Expecting xet://domain:user/[repo/[branch[/path]]], got {url}")
    
    if len(components) == 1 and expect_repo is True:
        raise ValueError(f"Invalid Xet URL format; user and repo must be specified. Expecting xet://domain:user/repo/[branch[/path]], got {url}")
    
    if len(components) > 1 and expect_repo is False:
        raise ValueError(f"Invalid Xet URL format for user; repo given.  Expecting xet://domain:user/, got {url}")
       
    if len(components) == 2 and expect_branch is True:
        raise ValueError(f"Invalid Xet URL format; user, repo, and branch must be specified for this operation. Expecting xet://domain:user/repo/branch[/path], got {url}")

    if len(components) > 2 and expect_branch is False:
        raise ValueError(f"Invalid Xet URL format for repo; branch given.  Expecting xet://domain:user/repo, got {url}")

    
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
