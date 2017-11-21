# -*- coding: utf-8 -*-


import os
import subprocess
import shlex
import logging
import vim

from completor import Completor


logger = logging.getLogger('completor')


_grep_esc_table = {c: '\\' + c for c in '*^$][.\\'}


def _escape_grep_regex(s):
    return s.translate(_grep_esc_table)


def _fuzzy_pattern(s):
    return '\\w*'.join([_escape_grep_regex(c) for c in s])


class CheckFeature(object):

    def __init__(self, name, command, input, expect):
        self.name = name
        self.command = command
        self.input = input
        self.expect = expect
        self.have = None

    def __bool__(self):
        if self.have is not None:
            return self.have

        proc = subprocess.run(self.command,
                              input=self.input,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

        self.have = self.expect(proc.stdout)

        if self.have:
            logger.info("tmux: detected %s", self.name)
        else:
            logger.info("tmux: no %s found. status=%r, stdout=%r, stderr=%r",
                        self.name, proc.returncode, proc.stdout, proc.stderr)

        return self.have


_have_gnu_xargs = CheckFeature('gnu-compatible xargs',
                               ['xargs', '-r', '-P0', 'echo'],
                               b'args_work',
                               lambda b: b.startswith(b'args_work'))


_have_grep_dash_o = CheckFeature('grep -o support',
                                 ['grep', '-o', r'\bx\w\+'],
                                 b'xy 1234 xz',
                                 b'xy\nxz\n'.__eq__)


def _get_script(prefix, grep_args='', fuzzy=False, exclude_pane=None):
    # list all panes
    s = "tmux list-panes -a -F '#{pane_id}'"
    if exclude_pane:
        # exclude given pane
        escaped = _escape_grep_regex(exclude_pane)
        s += ' | grep -v ' + shlex.quote('^' + escaped + '$')
    # capture panes
    if _have_gnu_xargs:
        s += ' | xargs -r -P0 -n1 tmux capture-pane -J -p -t'
    else:
        s += ' | xargs -n1 tmux capture-pane -J -p -t'
    if fuzzy:
        prefix_pattern = _fuzzy_pattern(prefix)
    else:
        prefix_pattern = _escape_grep_regex(prefix)
    # split words
    if _have_grep_dash_o:
        pattern = '\\b' + prefix_pattern + '\\w*'
        s += ' | grep ' + grep_args + ' -o -- ' + shlex.quote(pattern)
    else:
        s += r" | tr -c -s 'a-zA-Z0-9_' '\n'"
        # filter out words not beginning with pattern
        pattern = "^" + prefix_pattern
        s += ' | grep ' + grep_args + ' -- ' + shlex.quote(pattern)
    return s


def _get_completions(base, **kw):
    logger.info("tmux: base: %r", base)

    grep_args = ''
    if base.islower():
        grep_args = '-i'
    script = _get_script(base, grep_args=grep_args, **kw)

    logger.info("tmux: script: %r", script)

    proc = subprocess.run(["/bin/sh", "-c", script], shell=False,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

    logger.info("tmux: proc status: %r", proc.returncode)
    if proc.stderr:
        logger.info("tmux: stderr: %r", proc.stderr)

    output = proc.stdout
    res = output.split(b'\n')
    return res


class Tmux(Completor):
    filetype = 'common_tmux'
    sync = True

    def parse(self, base):
        try:
            this_pane = os.getenv('TMUX_PANE')
            fuzzy = vim.vars.get('completor_tmux_fuzzy', 1)

            res = _get_completions(base, fuzzy=fuzzy, exclude_pane=this_pane)

            return [{'word': token.decode('utf-8'), 'menu': '[TMUX]'}
                    for token in res]
        except Exception as e:
            logger.exception(e)
            raise
