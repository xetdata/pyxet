import os

from pyxet.sync import _join_to_absolute, _get_normalized_fs_protocol_and_path, SyncCommand


def test_join_to_absolute():
    def validate(root, rel, expected):
        full_path = _join_to_absolute(root, rel)
        assert full_path == expected

    validate('/', 'foo/bar.txt', '/foo/bar.txt')
    validate('/', '', '/')
    validate('/some/root', 'foo/bar.txt', '/some/root/foo/bar.txt')
    validate('/some/root', '', '/some/root/')


def test_get_normalized_fs_protocol_and_path(monkeypatch):
    def validate(uri, exp_proto, exp_path):
        fs, proto, path = _get_normalized_fs_protocol_and_path(uri)
        assert fs is not None
        assert proto == exp_proto
        assert fs.protocol == proto
        assert path == exp_path

    validate('/foo/bar/', 'file', '/foo/bar')
    validate('/', 'file', '/')
    validate('some/path', 'file', os.getcwd() + '/some/path')
    validate('.', 'file', os.getcwd())

    # Don't connect to S3.
    monkeypatch.setattr('pyxet.util._should_load_aws_credentials', lambda: False)
    validate('s3://bucket/obj', 's3', 'bucket/obj')
    validate('s3://bucket', 's3', 'bucket')
    validate('s3://bucket/dir/', 's3', 'bucket/dir')

    validate('xet://user/repo/branch', 'xet', 'user/repo/branch')
    validate('xet://user/repo/branch/sub/dir/', 'xet', 'user/repo/branch/sub/dir')
    validate('xet://user/repo/', 'xet', 'user/repo')


def test_sync_command_validate(monkeypatch):
    def validate(src, dst, is_valid):
        cmd = SyncCommand(src, dst, False, '', False)
        try:
            cmd.validate()
            assert is_valid
        except ValueError:
            assert not is_valid

    os.environ['XET_ENDPOINT'] = 'hub.xetsvc.com'

    validate('.', 'xet://XetHub/ReleaseTesting/main', True)
    validate('./sync_test.py', 'xet://XetHub/ReleaseTesting/main', False)
    validate('xet://XetHub/grapp2/main', 'xet://XetHub/ReleaseTesting/sync-branch/sync', False)
    validate('.', './other', False)
    validate('.', 'xet://XetHub/ReleaseTesting', False)
    validate('.', 'xet://', False)
    validate('./*', 'xet://XetHub/ReleaseTesting/main', False)
    validate('./*.py', 'xet://XetHub/ReleaseTesting/main', False)
    validate('.', 'xet://XetHub/ReleaseTesting/main/foo*', False)
    # TODO: may want to validate s3 paths when we have credentials
