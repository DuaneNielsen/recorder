#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
import subprocess
import urwid


def show_or_exit(key):
    if key in ('q', 'Q', 'esc'):
        raise urwid.ExitMainLoop()


def update_text(read_data):
    text.set_text(str(read_data))


def enter_idle():
    loop.remove_watch_file(pipe.stdout)


if __name__ == '__main__':
    widget = urwid.Pile([
        urwid.Button('Here is a button'),
        urwid.Button('And here another button'),
        urwid.Button('One more, just to be sure'),
        urwid.Button("Heck, let's add yet another one!"),
    ])
    text = urwid.Text('PROCESS OUTPUT:\n')
    widget = urwid.Columns([widget, text])
    widget = urwid.Filler(widget, 'top')

    loop = urwid.MainLoop(widget, unhandled_input=show_or_exit)
    stdout = loop.watch_pipe(update_text)
    stderr = loop.watch_pipe(update_text)
    pipe = subprocess.Popen('for i in $(seq 50); do echo -n "$i "; sleep 0.5; done',
                            shell=True, stdout=stdout, stderr=stderr)
    loop.run()