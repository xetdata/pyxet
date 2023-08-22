from pyxet.url_parsing import parse_url, get_url_info
from pyxet.file_system import env_login_token, env_login_user


def test_url_parses():
    for url in [
        "xet://u1@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "xet://u1@xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "https://u1@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "https://u1@xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "http://u1@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "http://u1@xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "xet://u1:pw@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "xet://u1:pw@xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "https://u1:pw@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "https://u1:pw@xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "http://u1:pw@xethub.com/u2/r1/b1/mydir/myfile.dat",
        "http://u1:pw@xethub.com/u2/r1.git/b1/mydir/myfile.dat",

        "xet://xethub.com/u2/r1/b1/mydir/myfile.dat",
        "xet://xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "https://xethub.com/u2/r1/b1/mydir/myfile.dat",
        "https://xethub.com/u2/r1.git/b1/mydir/myfile.dat",
        "http://xethub.com/u2/r1/b1/mydir/myfile.dat",
        "http://xethub.com/u2/r1.git/b1/mydir/myfile.dat",

        # These don't have the associated path
        "xet://u1@xethub.com/u2/r1",
        "xet://u1@xethub.com/u2/r1.git",
        "https://u1@xethub.com/u2/r1",
        "https://u1@xethub.com/u2/r1.git",
        "http://u1@xethub.com/u2/r1",
        "http://u1@xethub.com/u2/r1.git",
        "xet://u1:pw@xethub.com/u2/r1",
        "xet://u1:pw@xethub.com/u2/r1.git",
        "https://u1:pw@xethub.com/u2/r1",
        "https://u1:pw@xethub.com/u2/r1.git",
        "http://u1:pw@xethub.com/u2/r1",
        "http://u1:pw@xethub.com/u2/r1.git",

        "xet://xethub.com/u2/r1",
        "xet://xethub.com/u2/r1.git",
        "https://xethub.com/u2/r1",
        "https://xethub.com/u2/r1.git",
        "http://xethub.com/u2/r1",
        "http://xethub.com/u2/r1.git",

        # Trailing slash
        "xet://u1@xethub.com/u2/r1/b1/",
        "xet://u1@xethub.com/u2/r1.git/b1/",
        "https://u1@xethub.com/u2/r1/b1/",
        "https://u1@xethub.com/u2/r1.git/b1/",
        "http://u1@xethub.com/u2/r1/b1/",
        "http://u1@xethub.com/u2/r1.git/b1/",
        "xet://u1:pw@xethub.com/u2/r1/b1/",
        "xet://u1:pw@xethub.com/u2/r1.git/b1/",
        "https://u1:pw@xethub.com/u2/r1/b1/",
        "https://u1:pw@xethub.com/u2/r1.git/b1/",
        "http://u1:pw@xethub.com/u2/r1/b1/",
        "http://u1:pw@xethub.com/u2/r1.git/b1/",

        # These default to user u2
        "xet://xethub.com/u2/r1/b1/",
        "xet://xethub.com/u2/r1.git/b1/",
        "https://xethub.com/u2/r1/b1/",
        "https://xethub.com/u2/r1.git/b1/",
        "http://xethub.com/u2/r1/b1/",
        "http://xethub.com/u2/r1.git/b1/",

        # Subdirs with a
        "xet://u1@xethub.com/u2/r1/b1/altdir/",
        "xet://u1@xethub.com/u2/r1.git/b1/altdir/",
        "https://u1@xethub.com/u2/r1/b1/altdir/",
        "https://u1@xethub.com/u2/r1.git/b1/altdir/",
        "http://u1@xethub.com/u2/r1/b1/altdir/",
        "http://u1@xethub.com/u2/r1.git/b1/altdir/",
        "xet://u1:pw@xethub.com/u2/r1/b1/altdir/",
        "xet://u1:pw@xethub.com/u2/r1.git/b1/altdir/",
        "https://u1:pw@xethub.com/u2/r1/b1/altdir/",
        "https://u1:pw@xethub.com/u2/r1.git/b1/altdir/",
        "http://u1:pw@xethub.com/u2/r1/b1/altdir/",
        "http://u1:pw@xethub.com/u2/r1.git/b1/altdir/",
        "xet://xethub.com/u2/r1/b1/altdir/",
        "xet://xethub.com/u2/r1.git/b1/altdir/",
        "https://xethub.com/u2/r1/b1/altdir/",
        "https://xethub.com/u2/r1.git/b1/altdir/",
        "http://xethub.com/u2/r1/b1/altdir/",
        "http://xethub.com/u2/r1.git/b1/altdir/"

    ]:

        r = parse_url(url)
        xp = get_url_info(url)
        new_url = xp.full_url()
        xp2 = get_url_info(new_url)

        assert url.startswith(r['protocol'])

        if 'u1' in url:
            assert r['user'] == 'u1'
            assert xp.user == 'u1'
            assert xp2.user == 'u1'
        else:
            assert r['user'] is None
            assert xp.user == env_login_user()
            assert xp2.user == env_login_user()

        if 'pw' in url:
            assert r['token'] == 'pw'
            assert xp.token == 'pw'
            assert xp2.token == 'pw'
        else:
            assert r['token'] is None
            assert xp.token == env_login_token()
            assert xp2.token == env_login_token()

        assert r['repo'] == 'u2/r1'
        assert xp.repo == 'u2/r1'
        assert xp2.repo == 'u2/r1'

        if 'b1' in url:
            assert r['branch'] == 'b1'
            assert xp.branch == 'b1'
            assert xp2.branch == 'b1'
        else:
            assert r['branch'] is None
            assert xp.branch is None
            assert xp2.branch is None

        if 'mydir' in url:
            assert r['path'] == 'mydir/myfile.dat'
            assert xp.path == 'mydir/myfile.dat'
            assert xp2.path == 'mydir/myfile.dat'
        elif 'altdir' in url:
            assert r['path'] == 'altdir/'
            assert xp.path == 'altdir/'
            assert xp2.path == 'altdir/'
        else:
            assert r['path'] is None
            assert xp.path is None
            assert xp2.path is None
