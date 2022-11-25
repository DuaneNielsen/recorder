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
    response = urwid.Text(text)
    done = urwid.Button(u'Ok')
    urwid.connect_signal(done, 'click', handle_button, 'Stop Recording')
    return urwid.Filler(
        urwid.Pile([response, urwid.AttrMap(done, None, focus_map='reversed')])
    )


def handle_button(button, choice):
    if choice == 'Record':
        main.original_widget = recording_menu(['Stop Recording\n', f'{time}\n', f'{idle}\n', 'andmoredatadata\n'])

    if choice == 'Quit':
        exit_program(button)

    if choice == 'Stop Recording':
        main.original_widget = record_menu('I\'m baaaaack', choices)

time = 0
idle = 0

event_loop = urwid.SelectEventLoop()


def print_hello():
    global time
    time += 1
    event_loop.alarm(1, print_hello)


def increment_idle():
    global idle
    idle += 1


main = urwid.Padding(record_menu(u'Pythons', choices), left=2, right=2)
top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
                    align='center', width=('relative', 60),
                    valign='middle', height=('relative', 60),
                    min_width=20, min_height=9)
loop = urwid.MainLoop(top, palette=[('reversed', 'standout', ''), ], event_loop=event_loop)

event_loop.alarm(0, print_hello)
event_loop.enter_idle(increment_idle)
loop.run()