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
from urwid_app import UrwidFrontend, suppress_stdout_stderr

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


if __name__ == "__main__":

    class RecordingApp(UrwidFrontend):
        def __init__(self):
            super().__init__('SVO Recorder')
            choices = ['Stop Recording']
            self.add_subprocess('Recording', start_recording, choices)

        def handle_button(self, button, choice):

            if choice == 'Recording':
                self.main.original_widget = self.subprocess_menu['Recording'].menu()
                self.subprocess['Recording'].fork()

            if choice == 'Stop Recording' or choice == 'Return to Main':
                self.subprocess['Recording'].stop()
                self.main.original_widget = self.main_menu.menu()

            super().handle_button(button, choice)

        def heartbeat(self):
            """
            heartbeat that runs 24 times per second
            """

            # read from the process
            self.subprocess_menu['Recording'].item.append(self.subprocess['Recording'].read_pipe())

            # display it
            item = self.subprocess_menu['Recording'].item
            self.subprocess_menu['Recording'].update(['Recording...\n', f'{item} frames\n', ])
            self.loop.draw_screen()
            super().heartbeat()

    app = RecordingApp()
    app.run()