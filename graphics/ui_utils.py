import io
import traceback
from contextlib import contextmanager

import PySimpleGUI as sg

from .pnm import write_pnm
from .pnm.exceptions import *
from .utils import to_8bit


@contextmanager
def handle_exception(exit_on_error):
    try:
        yield
    except Exception as exc:
        if isinstance(exc, FileOpenError):
            error_text = "Error opening file"
        elif isinstance(exc, UnknownTagError):
            error_text = f"Unknown tag {exc.tag}"
        elif isinstance(exc, FormatError):
            error_text = f"Invalid {exc.file_part}"
        elif isinstance(exc, DataError):
            error_text = f"Invalid image ({exc.problem})"
        elif isinstance(exc, PnmError):
            error_text = "PNM error"
        else:
            error_text = "Unknown error"
        error = traceback.format_exc()
        sg.Window(
            "Error",
            [
                [sg.Text(error_text)],
                [sg.Multiline(error, size=(sg.MESSAGE_BOX_LINE_WIDTH, sg.MAX_SCROLLED_TEXT_BOX_HEIGHT))],
                [sg.P(), sg.Exit(), sg.P()],
            ],
            modal=True,
        ).read(close=True)
        if exit_on_error:
            exit(1)


def window_loop(window):
    while True:
        event, values = window.read()
        if event in [sg.WINDOW_CLOSED, "Exit", "Cancel"]:
            break
        yield event, values


@contextmanager
def open_window(window):
    yield window_loop(window)
    window.close()


def draw_image(graph, image_data):
    buffer = io.BytesIO()
    write_pnm(to_8bit(image_data), 255, buffer)
    graph.erase()
    graph.draw_image(data=buffer.getvalue(), location=(0, 0))


def require_filename(title, layout):
    window = sg.Window(title, layout, modal=True)
    with open_window(window) as evs:
        for event, values in evs:
            if event == "filename":
                window["done"].update(disabled=not values["filename"])
            if event == "done":
                return values
