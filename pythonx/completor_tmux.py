# -*- coding: utf-8 -*-


import os
import subprocess
import shlex
import logging

from completor import Completor


logger = logging.getLogger('completor')


_grep_esc_table = {c: '\\' + c for c in '*^$][.\\'}


def _escape_grep_regex(s):
    return s.translate(_grep_esc_table)


_have_gnu_xargs_result = None
def _have_gnu_xargs():
    global _have_gnu_xargs_result

    have = _have_gnu_xargs_result
    if have is not None:
        return have

    proc = subprocess.run(['xargs', '-r', '-P0', 'echo'],
                            input=b'args_work',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    have = proc.stdout.startswith(b'args_work')
    _have_gnu_xargs_result = have

    if have:
        logger.info("tmux: detected gnu-compatible xargs")
    else:
        logger.info("tmux: no gnu compatible xargs. "
                    "status=%r, stdout=%r, stderr=%r",
                    proc.returncode, proc.stdout, proc.stderr)

    return have


def _get_script(pattern, grep_args='', exclude_pane=None):
    # list all panes
    s = "tmux list-panes -a -F '#{pane_id}'"
    if exclude_pane:
        # exclude given pane
        escaped = _escape_grep_regex(exclude_pane)
        s += ' | grep -v ' + shlex.quote('^' + escaped + "$")
    # capture panes
    if _have_gnu_xargs():
        s += " | xargs -r -P0 -n1 tmux capture-pane -J -p -t"
    else:
        s += " | xargs -n1 tmux capture-pane -J -p -t"
    # split words
    s += " | tr -c -s 'a-zA-Z0-9_' '\\n'"
    # filter out words not beginning with pattern
    s += ' | grep ' + grep_args + ' -- ' + shlex.quote(pattern)
    return s


def _get_completions(base, **kw):
    logger.info("tmux: base: %r", base)

    grep_args = ''
    if base.islower():
        grep_args = '-i'
    pattern = '^' + _escape_grep_regex(base)
    script = _get_script(pattern, grep_args=grep_args, **kw)

    logger.info("tmux: script: %r", script)

    proc = subprocess.run(["/bin/bash", "-c", script], shell=False,
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
        if len(base) < 3:
            return []
        this_pane = os.getenv('TMUX_PANE')

        res = _get_completions(base, exclude_pane=this_pane)

        return [{'word': token.decode('utf-8'), 'menu': '[TMUX]'}
                for token in res]
