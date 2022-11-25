import os
import sys
from multiprocessing import Process, Pipe, Event
from collections import deque
import urwid


class suppress_stdout_stderr(object):
    """
    Supresses the stdout and stderr by piping them to dev null...
    The same place I send bad faith replies to my tweets
    """
    def __enter__(self):
        self.outnull_file = open(os.devnull, 'w')
        self.errnull_file = open(os.devnull, 'w')

        self.old_stdout_fileno_undup = sys.stdout.fileno()
        self.old_stderr_fileno_undup = sys.stderr.fileno()

        self.old_stdout_fileno = os.dup(sys.stdout.fileno())
        self.old_stderr_fileno = os.dup(sys.stderr.fileno())

        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        os.dup2(self.outnull_file.fileno(), self.old_stdout_fileno_undup)
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)

        sys.stdout = self.outnull_file
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

        os.dup2(self.old_stdout_fileno, self.old_stdout_fileno_undup)
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)

        os.close(self.old_stdout_fileno)
        os.close(self.old_stderr_fileno)

        self.outnull_file.close()
        self.errnull_file.close()


def subprocess_main(transmit, stop_process):
    with suppress_stdout_stderr():
        import time

        yup = ['yuuuup', 'yuuuuup', 'yeaup', 'yeoop']
        nope = ['noooooooe', 'noooope', 'nope', 'nope']
        mesg = 0
        i = 0

        while True:
            i = i % len(yup)
            if transmit.poll():
                mesg = transmit.recv()
            if mesg == 'Yup':
                transmit.send(yup[i])
            if mesg == 'Nope':
                transmit.send(nope[i])
            if stop_process.wait(0):
                break
            i += 1
            time.sleep(2)


class SubProcess:
    def __init__(self, main):
        """
        Handles forking, stopping and communication with a subprocess
        :param main: subprocess method to run method signature is

            def main(transmit, stop_process):
                transmit: is a multiprocess Pipe to send data to parent process
                stop_process: is multiprocess Event to set when you want the process to exit
        """
        self.main = main
        self.recv, self.transmit = None, None
        self.stop_process = None
        self.proc = None

    def fork(self):
        """
        Forks and starts the subprocess
        """
        self.recv, self.transmit = Pipe(duplex=True)
        self.stop_process = Event()
        self.proc = Process(target=self.main, args=(self.transmit, self.stop_process))
        self.proc.start()

    def write_pipe(self, item):
        self.recv.send(item)

    def read_pipe(self):
        """
        Reads data sent by the process into a list and returns it
        :return:
        """
        item = []
        if self.recv is not None:
            try:
                while self.recv.poll():
                    item += [self.recv.recv()]
            except:
                pass
        return item

    def stop(self):
        """
        Sets the event to tell the process to exit.
        note: this is co-operative multi-tasking, the process must respect the flag or this won't work!
        """
        self.stop_process.set()
        self.proc.join()


class UrwidFrontend:
    def __init__(self, subprocess_main):
        """
        Urwid frontend to control the subprocess and display it's output
        """
        self.title = 'Urwid Frontend Demo'
        self.choices = 'Start Subprocess|Quit'.split('|')
        self.response = None
        self.item = deque(maxlen=10)
        self.event_loop = urwid.SelectEventLoop()

        # start the heartbeat
        self.event_loop.alarm(0, self.heartbeat)
        self.main = urwid.Padding(self.main_menu(), left=2, right=2)
        self.top = urwid.Overlay(self.main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
                                 align='center', width=('relative', 60),
                                 valign='middle', height=('relative', 60),
                                 min_width=20, min_height=9)

        self.loop = urwid.MainLoop(self.top, palette=[('reversed', 'standout', ''), ], event_loop=self.event_loop)

        self.subprocess = SubProcess(subprocess_main)

    def exit_program(self, button):
        raise urwid.ExitMainLoop()

    def main_menu(self):
        body = [urwid.Text(self.title), urwid.Divider()]
        for c in self.choices:
            button = urwid.Button(c)
            urwid.connect_signal(button, 'click', self.handle_button, c)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    def subproc_menu(self):
        self.response = urwid.Text('Waiting ...')
        body = [self.response, urwid.Divider()]
        choices = ['Yup', 'Nope', 'Stop Subprocess']
        for c in choices:
            button = urwid.Button(c)
            urwid.connect_signal(button, 'click', self.handle_button, c)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        return listbox

    def update_subproc_menu(self, text):
        self.response.set_text(text)

    def handle_button(self, button, choice):
        if choice == 'Start Subprocess':
            self.main.original_widget = self.subproc_menu()
            self.subprocess.fork()
            self.item = deque(maxlen=10)

        if choice == 'Stop Subprocess':
            self.subprocess.stop()
            self.main.original_widget = self.main_menu()

        if choice == 'Quit':
            self.exit_program(button)

        if choice == 'Yup':
            self.subprocess.write_pipe('Yup')

        if choice == 'Nope':
            self.subprocess.write_pipe('Nope')

    def heartbeat(self):
        """
        heartbeat that runs 24 times per second
        """

        # read from the process
        self.item.append(self.subprocess.read_pipe())

        # display it
        if self.response is not None:
            self.update_subproc_menu(['Subprocess started\n', f'{self.item}\n', ])
            self.loop.draw_screen()

        # set the next beat
        self.event_loop.alarm(1 / 24, self.heartbeat)

    def run(self):
        self.loop.run()


if __name__ == "__main__":

    app = UrwidFrontend(subprocess_main)
    app.run()
