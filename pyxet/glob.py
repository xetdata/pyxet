import fnmatch
import re

import pyxet


def _join(*args):
    return '/'.join(args)


def iglob(pattern):
    remote, user, repo, branch, basename = pyxet._parse_path(pattern, allow_empty_path=True)
    repo_key = '/'.join([remote, user, repo, branch])
    pathway = [repo_key] + basename.split('/')

    def _valid_dir(file_type, file_name, current_name):
        if file_type != 'directory':
            return False
        return current_name == '**' \
               or current_name == file_name.split('/')[-1] \
               or current_name == repo_key

    def _iglob(path, level: int = 0):
        """
        @param path: a valid path
        @param level: a pathway level to conisder
        @return:
        """
        if level == len(pathway) + 1 or pathway[level] == '':
            return
        info = pyxet.info(path, allow_empty_path=True)
        compare_path = path
        if info['type'] == 'directory':
            if pattern.endswith('/'):  # we iterate without '/' -> following the relevant case
                compare_path = path + '/'
            elif pattern.endswith('*'):  # edge case for "path*"                    
                compare_path = path[:-1]
        if fnmatch.fnmatch(compare_path, pattern):
            yield compare_path
            return

        if _valid_dir(info['type'], info['name'], pathway[level]):
            for file in pyxet.ls(path, detail=True, exist_ok=True):
                for ipath in _iglob(_join(path, file['name']), level + 1):
                    yield ipath

    for ipath in _iglob(repo_key, 0):
        yield ipath


def glob(pattern):
    return list(iglob(pattern))


# TODO might not need this
def _listdir(path: str):
    """
    Recursively finds all files and directories in the given path that match the given glob pattern.

    Args:
        path (str): The path to search.
        pattern (str): The glob pattern to match.

    Returns:
        list: A list of all files and directories found.
    """
    results = []
    for file in pyxet.ls(path, detail=True, exist_ok=True):
        file_path = _join(path, file['name'])
        if file['type'] == 'directory':
            results.append(file_path)
            results.extend(_listdir(file_path))
        else:
            results.append(file_path)
    return results


# TODO  might not need this
def glob_to_regex(pattern):
    # Escape all special characters in the glob pattern
    pattern = re.escape(pattern)
    # Replace glob-specific wildcards with regex equivalents
    pattern = pattern.replace('\\*', '.*')
    pattern = pattern.replace('\\?', '.')
    # Add anchors to match the whole string
    pattern = '^' + pattern + '$'
    return re.compile(pattern)
