"""
Provides URL parsing for Xet Repos
"""
import unittest
from collections import namedtuple
from urllib.parse import urlparse
import sys

class XetPathInfo:
    __slots__ = ['scheme', 'domain', 'token', 'user', 'repo', 'branch', 'path']

    def url(self):
        url = f"{self.scheme}://{self.user}@{self.domain}/{self.repo}/"
        if self.branch:
            url = f"{url}/{self.branch}"
        if self.path:
            url = f"{url}/{self.path}"

        return url

    def remote(self):
        url = f"{self.scheme}://{self.user}@{self.domain}/{self.repo}"


has_warned_user_on_url_format = False

def parse_url(url, default_domain='xethub.com', partial_remote=False, recursive_skip_checks = False):
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

    url = url.lstrip('/')
    parse = urlparse(url)
    if parse.scheme == '':
        parse = parse._replace(scheme='xet')

    # support default_domain with a scheme (http/https)
    domain_split = default_domain.split('://')
    scheme = 'https'
    if len(domain_split) == 2:
        scheme = domain_split[0]
        default_domain = domain_split[1]

    if parse.scheme != 'xet':
        raise ValueError('Invalid protocol')

    # Set this as a default below     

    ret = XetPathInfo()
    # Set what defaults we can
    ret.domain = default_domain
    ret.scheme = "xet"


    # Handle the case where we are xet://user/repo. In which case the domain
    # parsed is not xethub.com and domain="user".
    # we rewrite the parse the handle this case early.
    if "@" not in parse.netloc:
        if not recursive_skip_checks:
            global has_warned_user_on_url_format
            
            if not has_warned_user_on_url_format:
                sys.stderr.write("Warning:  The use of the xet:// prefix without an endpoint is deprecated and will be disabled in the future.\n"
                                f"          Please switch URLs to use the format xet://<user>@<endpoint>/<repo>/<branch>/<path>.\n"
                                f"          Endpoint now defaulting to {default_domain}.\n\n")
                has_warned_user_on_url_format = True

        if parse.netloc.endswith(".com"):  # Cheap way now to see if it's a website or not; we won't hit this with the new format.
            ret.domain = parse.netloc
            path_to_parse = parse.path
        else:
            ret.domain = default_domain
            path_to_parse = "f{parse.netloc}/{parse.path}"
    else:
        
        # Hack until we can clean up this parsing logic
        user_at_domain = parse.netloc.split("@")
        if len(user_at_domain) == 2:
            ret.user, ret.domain = user_at_domain
            path_to_parse = f"{ret.user}/{parse.path}"
        else: 
            raise ValueError(f"Cannot parse user and endpoint from {parse.netloc}")

    
    ret = XetPathInfo()
    ret.domain = domain
    

    # Split the known path and try to split out the user/repo/branch/path components
    path = parse.path

    path_endswith_slash = path.endswith("/")

    components = list([t for t in [t.strip() for t in path.split('/')] if t])

    # so the minimum for a remote is xethub.com/user/
    if len(components) < 2:
        if partial_remote and len(components) >= 1:
            replacement_parse_path = '/'.join(components)
            parse = parse._replace(path=replacement_parse_path, scheme=scheme)
            return XetPathInfo(parse.geturl(), "", "")
        raise ValueError(f"Invalid Xet URL format: Expecting xet://user@domain/repo/[branch]/[path], got {url}")

    branch = ""
    if len(components) >= 3:
        branch = components[2]  

    path = ""
    if len(components) >= 4:
        path = '/'.join(components[3:])

    if path and path_endswith_slash: 
        path = path + '/'

    # we leave url with the first 2 components. i.e. "/user/repo"
    replacement_parse_path = '/'.join(components[:2])
    parse = parse._replace(path=replacement_parse_path, scheme=scheme)

    ret.domain = domain

    return ret

class ParseUrlTest(unittest.TestCase):

    def parse_url(self, url, expect_warning, **kwargs):
        global has_warned_user_on_url_format
        has_warned_user_on_url_format = False
        parse = parse_url(url, **kwargs)
        self.assertEqual(has_warned_user_on_url_format, expect_warning)
        print(f"Test parse result = {parse}")
        return parse

    def test_parse_xet_url(self):
        parse = self.parse_url("xet://xethub.com/user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://xethub.com/user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://xethub.com/user/repo/branch/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo/branch", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo/branch", True, default_domain='xetbeta.com')
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://xethub.com/user", True)

    def test_parse_xet_url_truncated(self):
        parse = self.parse_url("xet://user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://user/repo/branch/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo/branch", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo/branch", True, default_domain='xetbeta.com')
        self.assertEqual(parse.remote, "https://xetbeta.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://user", True)

    def test_parse_plain_path(self):
        parse = self.parse_url("/user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("/user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("/user/repo/branch/", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo/branch", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo", True)
        self.assertEqual(parse.remote, "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo/branch", True, default_domain='xetbeta.com')
        self.assertEqual(parse.remote, "https://xetbeta.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://xethub.com/user", True)
    
    def test_parse_xet_url_correct(self):
        parse = self.parse_url("xet://user@xh.com/repo/branch/hello/world", False)
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://user@xh.com/repo/branch/hello/world/", False)
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://user@xh.com/repo/branch/", False)
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user@xh.com/repo/branch", False)
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user@xh.com/repo", False)
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://XetHub@hub.xetsvc.com/Flickr30k/main", False)
        self.assertEqual(parse.remote, "https://hub.xetsvc.com/XetHub/Flickr30k")
        self.assertEqual(parse.branch, "main")
        self.assertEqual(parse.path, "")


        parse = self.parse_url("xet://user@xh.com/repo/branch", False, default_domain='xetbeta.com')
        self.assertEqual(parse.remote, "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")
