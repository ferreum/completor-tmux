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


def _get_script(pattern, grep_args='', exclude_pane=None):
    # list all panes
    s = "tmux list-panes -a -F '#{pane_id}'"
    if exclude_pane:
        # exclude given pane
        escaped = _escape_grep_regex(exclude_pane)
        s += ' | grep -v ' + shlex.quote('^' + escaped + "$")
    # capture panes
    s += " | xargs -r -P0 -n1 tmux capture-pane -J -p -t"
    # split words
    s += " | tr -c -s 'a-zA-Z0-9_' '\\n'"
    # filter out words not beginning with pattern
    s += ' | grep ' + grep_args + ' -- ' + shlex.quote(pattern)
    return s


def _get_completions(base, **kw):
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

    def parse(self, base):
        if len(base) < 3:
            return []
        this_pane = os.getenv('TMUX_PANE')

        res = _get_completions(base, exclude_pane=this_pane)

        return [{'word': token.decode('utf-8'), 'menu': '[TMUX]'}
                for token in res]
