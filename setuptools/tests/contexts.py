import tempfile
import os
import shutil
import sys
import contextlib
import site
import io

import pkg_resources
from filelock import FileLock


@contextlib.contextmanager
def tempdir(cd=lambda dir: None, **kwargs):
    temp_dir = tempfile.mkdtemp(**kwargs)
    orig_dir = os.getcwd()
    try:
        cd(temp_dir)
        yield temp_dir
    finally:
        cd(orig_dir)
        shutil.rmtree(temp_dir)


@contextlib.contextmanager
def environment(**replacements):
    """
    In a context, patch the environment with replacements. Pass None values
    to clear the values.
    """
    saved = dict(
        (key, os.environ[key])
        for key in replacements
        if key in os.environ
    )

    # remove values that are null
    remove = (key for (key, value) in replacements.items() if value is None)
    for key in list(remove):
        os.environ.pop(key, None)
        replacements.pop(key)

    os.environ.update(replacements)

    try:
        yield saved
    finally:
        for key in replacements:
            os.environ.pop(key, None)
        os.environ.update(saved)


@contextlib.contextmanager
def quiet():
    """
    Redirect stdout/stderr to StringIO objects to prevent console output from
    distutils commands.
    """

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    new_stdout = sys.stdout = io.StringIO()
    new_stderr = sys.stderr = io.StringIO()
    try:
        yield new_stdout, new_stderr
    finally:
        new_stdout.seek(0)
        new_stderr.seek(0)
        sys.stdout = old_stdout
        sys.stderr = old_stderr


@contextlib.contextmanager
def save_user_site_setting():
    saved = site.ENABLE_USER_SITE
    try:
        yield saved
    finally:
        site.ENABLE_USER_SITE = saved


@contextlib.contextmanager
def save_pkg_resources_state():
    pr_state = pkg_resources.__getstate__()
    # also save sys.path
    sys_path = sys.path[:]
    try:
        yield pr_state, sys_path
    finally:
        sys.path[:] = sys_path
        pkg_resources.__setstate__(pr_state)


@contextlib.contextmanager
def suppress_exceptions(*excs):
    try:
        yield
    except excs:
        pass


@contextlib.contextmanager
def session_locked_tmp_dir(tmp_path_factory, name):
    """Uses a file lock to guarantee only one worker can access a temp dir"""
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    # ^-- get the temp directory shared by all workers
    locked_dir = root_tmp_dir / name
    with FileLock(locked_dir.with_suffix(".lock")):
        # ^-- prevent multiple workers to access the directory at once
        locked_dir.mkdir(exist_ok=True, parents=True)
        yield locked_dir
