########################################################################
#
# Copyright (c) 2022, STEREOLABS.
#
# All rights reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################

import sys
from signal import signal, SIGINT
import pathlib
from pathlib import Path
from multiprocessing import Process, Pipe, Event


def _counter():
    """
    counter to keep track of run id
    creates a file .run_id in the current directory which stores the most recent id
    """
    home = pathlib.Path.home()
    run_id_pid = Path(f'{home}/Documents/ZED/.run_id')
    count = 1
    if run_id_pid.exists():
        with run_id_pid.open('r+') as f:
            last_id = int(f.readline())
            last_id += 1
            count = last_id
            f.seek(0)
            f.write(str(last_id))
    else:
        with run_id_pid.open('w+') as f:
            f.write(str(count))
    return count


import os
import sys


class suppress_stdout_stderr(object):
    def __enter__(self):
        self.outnull_file = open(os.devnull, 'w')
        self.errnull_file = open(os.devnull, 'w')

        self.old_stdout_fileno_undup    = sys.stdout.fileno()
        self.old_stderr_fileno_undup    = sys.stderr.fileno()

        self.old_stdout_fileno = os.dup ( sys.stdout.fileno() )
        self.old_stderr_fileno = os.dup ( sys.stderr.fileno() )

        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        os.dup2 ( self.outnull_file.fileno(), self.old_stdout_fileno_undup )
        os.dup2 ( self.errnull_file.fileno(), self.old_stderr_fileno_undup )

        sys.stdout = self.outnull_file
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

        os.dup2 ( self.old_stdout_fileno, self.old_stdout_fileno_undup )
        os.dup2 ( self.old_stderr_fileno, self.old_stderr_fileno_undup )

        os.close ( self.old_stdout_fileno )
        os.close ( self.old_stderr_fileno )

        self.outnull_file.close()
        self.errnull_file.close()


def start_recording(transmit, event):
    with suppress_stdout_stderr():
        import pyzed.sl as sl
        cam = sl.Camera()

        def handler(signal_received, frame):
            cam.disable_recording()
            cam.close()
            sys.exit(0)

        signal(SIGINT, handler)

        frames_recorded = 0
        home = pathlib.Path.home()
        counter = _counter()

        filename = f'{home}/Documents/ZED/{counter}.svo'

        init = sl.InitParameters()
        init.camera_resolution = sl.RESOLUTION.HD720
        init.depth_mode = sl.DEPTH_MODE.NONE

        status = cam.open(init)
        if status != sl.ERROR_CODE.SUCCESS:
            exit(1)

        recording_param = sl.RecordingParameters(filename, sl.SVO_COMPRESSION_MODE.H264)
        err = cam.enable_recording(recording_param)
        if err != sl.ERROR_CODE.SUCCESS:
            exit(1)

        runtime = sl.RuntimeParameters()

        while True:
            if cam.grab(runtime) == sl.ERROR_CODE.SUCCESS:
                frames_recorded += 1
                transmit.send(frames_recorded)

            if event.wait(timeout=0):
                cam.disable_recording()
                cam.close()
                sys.exit(0)


# global variables
recording_proc, recv, event, item, response = None, None, None, None, None


if __name__ == "__main__":

    import urwid

    choices = u'Record Quit'.split()

    def exit_program(button):
        raise urwid.ExitMainLoop()


    def record_menu(title, choices):
        body = [urwid.Text(title), urwid.Divider()]
        for c in choices:
            button = urwid.Button(c)
            urwid.connect_signal(button, 'click', handle_button, c)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        return urwid.ListBox(urwid.SimpleFocusListWalker(body))


    def recording_menu(text):
        global response
        response = urwid.Text(text)
        done = urwid.Button(u'Stop Recording')
        urwid.connect_signal(done, 'click', handle_button, 'Stop Recording')
        return urwid.Filler(
            urwid.Pile([response, urwid.AttrMap(done, None, focus_map='reversed')])
        )


    def handle_button(button, choice):
        print(choice)
        global recording_proc, recv, event, item
        if choice == 'Record':
            main.original_widget = recording_menu(['Recording frame\n', f'{item}\n',])
            recording_proc, recv, event = fork_recorder()
            item = 0

        if choice == 'Quit':
            exit_program(button)

        if choice == 'Stop Recording':
            event.set()
            recording_proc.join()
            main.original_widget = record_menu('Record SVO', choices)

    def read_pipe():
        # print('read pipe')
        global recv, event, item, response
        if recv is not None:
            try:
                while recv.poll():
                    item = recv.recv()
            except:
                item = 0
            if response is not None:
                response.set_text(['Recording frame\n', f'{item}\n', ])
            loop.draw_screen()
        event_loop.alarm(1, read_pipe)

    def fork_recorder():
        recv, transmit = Pipe()
        event = Event()
        recording_proc = Process(target=start_recording, args=(transmit, event))
        recording_proc.start()
        return recording_proc, recv, event


    event_loop = urwid.SelectEventLoop()
    event_loop.alarm(0, read_pipe)

    main = urwid.Padding(record_menu(u'Pythons', choices), left=2, right=2)
    top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
                        align='center', width=('relative', 60),
                        valign='middle', height=('relative', 60),
                        min_width=20, min_height=9)
    loop = urwid.MainLoop(top, palette=[('reversed', 'standout', ''), ], event_loop=event_loop)
    loop.run()
