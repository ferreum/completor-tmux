# -*- coding: utf-8 -*-


import os
import subprocess
import shlex

from completor import Completor


_grep_esc_table = {c: '\\' + c for c in '*^$][.\\'}


def _escape_grep_regex(s):
    return s.translate(_grep_esc_table)


def _get_script(pattern, minlen=3, grep_args='', exclude_pane=None):
    # list all panes
    s = "tmux list-panes -a -F '#{pane_id}'"
    if exclude_pane:
        # exclude given pane
        escaped = _escape_grep_regex(exclude_pane)
        s += ' | grep -v ' + shlex.quote('^' + escaped + "$")
    # capture panes
    s += " | xargs -r -P0 -n1 tmux capture-pane -J -p -t"
    # copy lines and split words
    s += " | sed -e 'p;s/[^a-zA-Z0-9_]/ /g'"
    # split on spaces
    s += " | tr -s '[:space:]' '\\n'"
    # remove surrounding non-word characters
    s += ' | grep -o "\\w.*\\w"'
    # filter out words not beginning with pattern
    s += ' | grep ' + grep_args + ' -- ' + shlex.quote(pattern)
    # filter out short words
    s += " | awk 'length($0) >= %d'" % minlen
    return s


def _get_completions(base, **kw):
    grep_args = ''
    if base.islower():
        grep_args = '-i'
    pattern = '^' + _escape_grep_regex(base)
    script = _get_script(pattern, grep_args=grep_args, **kw)
    output = subprocess.check_output(["/bin/bash", "-c", script],
                                     shell=False)
    res = output.split(b'\n')
    return res


class Tmux(Completor):
    filetype = 'common_tmux'

    def parse(self, base):
        if len(base) < 3:
            return []
        this_pane = os.getenv('TMUX_PANE')

        res = _get_completions(base, minlen=3, exclude_pane=this_pane)

        return [{'word': token.decode('utf-8'), 'menu': '[TMUX]'}
                for token in res]
