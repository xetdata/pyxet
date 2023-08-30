import os

import pyxet
from pyxet.sync import _join_to_absolute, _get_normalized_fs_protocol_and_path, SyncCommand

from utils import CONSTANTS, require_s3_creds


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


def check_sync_validate(src, dst, is_valid):
    cmd = SyncCommand(src, dst, False, '', False)
    try:
        cmd.validate()
        assert is_valid
    except (ValueError, FileNotFoundError):
        assert not is_valid


def test_sync_command_validate_local():
    pyxet.login(CONSTANTS.TESTING_USERNAME, CONSTANTS.TESTING_TOKEN, email="a@a.com")

    check_sync_validate('.', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', True)
    check_sync_validate('/nonexistent', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate('./sync_test.py', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate('xet://XetHub/grapp2/main', f'xet://{CONSTANTS.TESTING_SYNCREPO}/sync-branch/sync', False)
    check_sync_validate('.', f'xet://{CONSTANTS.TESTING_SYNCREPO}/nonexistent-branch', False)
    check_sync_validate('.', './other', False)
    check_sync_validate('.', f'xet://{CONSTANTS.TESTING_SYNCREPO}', False)
    check_sync_validate('.', 'xet://', False)
    check_sync_validate('./*', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate('./*.py', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate('.', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main/foo*', False)


@require_s3_creds()
def test_sync_command_validate_s3():
    pyxet.login(CONSTANTS.TESTING_USERNAME, CONSTANTS.TESTING_TOKEN, email="a@a.com")

    check_sync_validate(f's3://{CONSTANTS.S3_BUCKET}', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', True)
    check_sync_validate(f's3://{CONSTANTS.S3_BUCKET}/nonexistent-path', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate(f's3://', f'xet://{CONSTANTS.TESTING_SYNCREPO}/main', False)
    check_sync_validate(f's3://{CONSTANTS.S3_BUCKET}', f's3://{CONSTANTS.S3_BUCKET}/other', False)

