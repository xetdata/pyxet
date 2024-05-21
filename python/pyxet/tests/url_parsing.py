import pyxet.url_parsing as url_parsing
import unittest

class TestUrlParsing(unittest.TestCase):

    def parse_url(self, url, expect_warning, **kwargs):
        url_parsing.has_warned_user_on_url_format = False
        parse = url_parsing.parse_url(url, **kwargs)
        self.assertEqual(url_parsing.has_warned_user_on_url_format, expect_warning)
        print(f"Test parse result = {parse}")

        self.assertEqual(parse, url_parsing.parse_url(parse.url()))
        return parse

    def test_parse_xet_url(self):
        parse = self.parse_url("xet://xethub.com/user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://xethub.com/user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://xethub.com/user/repo/branch/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo/branch", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xethub.com/user/repo/branch", True, default_endpoint='xetbeta.com')
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://xethub.com/user", True)

    def test_parse_xet_url_truncated(self):
        parse = self.parse_url("xet://user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://user/repo/branch/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo/branch", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://user/repo/branch", True, default_endpoint='xetbeta.com')
        self.assertEqual(parse.remote(), "https://xetbeta.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://user", True)

    def test_parse_plain_path(self):
        parse = self.parse_url("/user/repo/branch/hello/world", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("/user/repo/branch/hello/world/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("/user/repo/branch/", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo/branch", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo", True)
        self.assertEqual(parse.remote(), "https://xethub.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("/user/repo/branch", True, default_endpoint='xetbeta.com')
        self.assertEqual(parse.remote(), "https://xetbeta.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        with self.assertRaises(ValueError):
            self.parse = self.parse_url("xet://xethub.com/user", True)

    def test_parse_xet_url_correct(self):
        parse = self.parse_url("xet://xh.com:user/repo/branch/hello/world", False)
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world")

        parse = self.parse_url("xet://xh.com:user/repo/branch/hello/world/", False)
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "hello/world/")

        parse = self.parse_url("xet://xh.com:user/repo/branch/", False)
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xh.com:user/repo/branch", False)
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://xh.com:user/repo", False)
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "")
        self.assertEqual(parse.path, "")

        parse = self.parse_url("xet://hub.xetsvc.com:XetHub/Flickr30k/main", False)
        self.assertEqual(parse.remote(), "https://hub.xetsvc.com/XetHub/Flickr30k")
        self.assertEqual(parse.branch, "main")
        self.assertEqual(parse.path, "")


        parse = self.parse_url("xet://xh.com:user/repo/branch", False, default_endpoint='xetbeta.com')
        self.assertEqual(parse.remote(), "https://xh.com/user/repo")
        self.assertEqual(parse.branch, "branch")
        self.assertEqual(parse.path, "")

