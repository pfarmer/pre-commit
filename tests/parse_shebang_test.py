from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import distutils.spawn
import io
import os
import sys

import pytest

from pre_commit import parse_shebang
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.util import make_executable


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        (b'', ()),
        (b'#!/usr/bin/python', ('/usr/bin/python',)),
        (b'#!/usr/bin/env python', ('python',)),
        (b'#! /usr/bin/python', ('/usr/bin/python',)),
        (b'#!/usr/bin/foo  python', ('/usr/bin/foo', 'python')),
        (b'\xf9\x93\x01\x42\xcd', ()),
        (b'#!\xf9\x93\x01\x42\xcd', ()),
        (b'#!\x00\x00\x00\x00', ()),
    ),
)
def test_parse_bytesio(s, expected):
    assert parse_shebang.parse_bytesio(io.BytesIO(s)) == expected


def test_file_doesnt_exist():
    assert parse_shebang.parse_filename('herp derp derp') == ()


def test_file_not_executable(tmpdir):
    x = tmpdir.join('f')
    x.write_text('#!/usr/bin/env python', encoding='UTF-8')
    assert parse_shebang.parse_filename(x.strpath) == ()


def test_simple_case(tmpdir):
    x = tmpdir.join('f')
    x.write_text('#!/usr/bin/env python', encoding='UTF-8')
    make_executable(x.strpath)
    assert parse_shebang.parse_filename(x.strpath) == ('python',)


def test_normexe_does_not_exist():
    with pytest.raises(OSError) as excinfo:
        parse_shebang.normexe('i-dont-exist-lol')
    assert excinfo.value.args == ('Executable i-dont-exist-lol not found',)


def test_normexe_already_full_path():
    assert parse_shebang.normexe(sys.executable) == sys.executable


def test_normexe_gives_full_path():
    expected = distutils.spawn.find_executable('echo')
    assert parse_shebang.normexe('echo') == expected
    assert os.sep in expected


def test_normalize_cmd_trivial():
    cmd = (distutils.spawn.find_executable('echo'), 'hi')
    assert parse_shebang.normalize_cmd(cmd) == cmd


def test_normalize_cmd_PATH():
    cmd = ('python', '--version')
    expected = (distutils.spawn.find_executable('python'), '--version')
    assert parse_shebang.normalize_cmd(cmd) == expected


def write_executable(shebang):
    os.mkdir('bin')
    path = os.path.join('bin', 'run')
    with io.open(path, 'w') as f:
        f.write('#!{0}'.format(shebang))
    make_executable(path)
    return path


@contextlib.contextmanager
def bin_on_path():
    bindir = os.path.join(os.getcwd(), 'bin')
    with envcontext((('PATH', (bindir, os.pathsep, Var('PATH'))),)):
        yield


def test_normalize_cmd_shebang(in_tmpdir):
    python = distutils.spawn.find_executable('python')
    path = write_executable(python)
    assert parse_shebang.normalize_cmd((path,)) == (python, path)


def test_normalize_cmd_PATH_shebang_full_path(in_tmpdir):
    python = distutils.spawn.find_executable('python')
    path = write_executable(python)
    with bin_on_path():
        ret = parse_shebang.normalize_cmd(('run',))
        assert ret == (python, os.path.abspath(path))


def test_normalize_cmd_PATH_shebang_PATH(in_tmpdir):
    python = distutils.spawn.find_executable('python')
    path = write_executable('/usr/bin/env python')
    with bin_on_path():
        ret = parse_shebang.normalize_cmd(('run',))
        assert ret == (python, os.path.abspath(path))
