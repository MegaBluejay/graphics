import io
import traceback
from contextlib import contextmanager

import numpy as np
import PySimpleGUI as sg

from .colors import Image, color_modes, convert_color
from .pnm import open_pnm_file, read_pnm, write_pnm
from .pnm.exceptions import *
from .utils import normalize, to_8bit


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


sg.theme("DarkGray15")
get_image_info_layout = [
    [sg.Text("Filename")],
    [sg.Input(key="filename", enable_events=True), sg.FileBrowse(target="filename")],
    [sg.Listbox(values=color_modes, default_values=["rgb"], size=(10, 5), key="color_mode")],
    [sg.Button("OK", key="done", disabled=True), sg.Cancel()],
]
values = require_filename("Open PNM", get_image_info_layout)
if not values:
    exit()
filename, color_mode = values["filename"], values["color_mode"][0]
with handle_exception(exit_on_error=True):
    with open_pnm_file(filename, "rb") as file:
        image_data, max_val = read_pnm(file)
    h, w = image_data.shape[:2]
    image_data = normalize(image_data, max_val)
    image = Image(image_data, color_mode)

layout = [
    [sg.Graph((w, h), (0, h - 1), (w - 1, 0), key="graph")],
    [
        sg.Column(
            [
                [sg.Text("Show as")],
                [
                    sg.Listbox(
                        values=color_modes,
                        default_values=[color_mode],
                        size=(10, 5),
                        enable_events=True,
                        key="color_mode",
                    )
                ],
            ],
        ),
        sg.Column(
            [
                [sg.Text("Channel")],
                [
                    sg.Listbox(
                        values=["All", "1", "2", "3"],
                        enable_events=True,
                        default_values=["All"],
                        size=(5, 3),
                        key="channel",
                    )
                ],
            ],
        ),
    ],
    [sg.Button("Save", key="save"), sg.Exit()],
]

window = sg.Window("PNM", layout, finalize=True, element_justification="center")
draw_image(window["graph"], image[color_mode])
with open_window(window) as evs:
    for event, values in evs:
        if event == "color_mode":
            window["channel"].update(set_to_index=0)
            color_mode = values["color_mode"][0]
            draw_image(window["graph"], image[color_mode])
        if event == "channel":
            channel = values["channel"][0]
            if channel == "All":
                draw_image(window["graph"], image[color_mode])
            else:
                draw_image(window["graph"], image[color_mode][:, :, int(channel) - 1])
        if event == "save":
            save_layout = [
                [sg.Input(key="filename", enable_events=True), sg.SaveAs(target="filename")],
                [sg.Button("Save", key="done", disabled=True), sg.Cancel()],
            ]
            save_values = require_filename("Save PNM", save_layout)
            if save_values:
                filename = save_values["filename"]
                with handle_exception(exit_on_error=False):
                    with open_pnm_file(filename, "wb") as file:
                        write_pnm(to_8bit(image[color_mode]), 255, file)
