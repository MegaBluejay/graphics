import io
import traceback

import numpy as np
import PySimpleGUI as sg

from .colors import color_modes, convert_color
from .pnm import open_pnm_file, read_pnm, write_pnm
from .pnm.exceptions import *
from .utils import *


def handle_exception(exc):
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
    ).read(close=True)


sg.theme("DarkGray15")

event, values = sg.Window(
    "Open PNP",
    [
        [sg.Text("Filename")],
        [sg.Input(k="filename"), sg.FileBrowse(target="filename")],
        [sg.Text("Open as")],
        [sg.Listbox(values=color_modes, size=(30, 5), key="color_mode")],
        [sg.OK(), sg.Cancel()],
    ],
).read(close=True)
if event != "OK":
    exit()
filename = values["filename"]
color_mode = values["color_mode"][0]
buffer = io.BytesIO()
try:
    with open_pnm_file(filename, "rb") as file:
        image, max_val = read_pnm(file)
    if len(image.shape) != 2:
        image = normalize(image, max_val)
        image = convert_color(image, color_mode, "rgb")
    image = to_8bit(image)
    write_pnm(image, max_val, buffer)
except Exception as exc:
    handle_exception(exc)
else:
    new_color_mode = None
    channel = None
    while True:
        event, values = sg.Window(
            "PNP",
            [
                [sg.Image(data=buffer.getvalue())],
                [sg.Text("Show as")],
                [
                    sg.Listbox(
                        values=color_modes,
                        default_values=[
                            color_mode if new_color_mode is None else new_color_mode,
                        ],
                        size=(30, 5),
                        enable_events=True,
                        key="color_mode",
                    )
                ],
                [sg.Text("Select channel")],
                [
                    sg.Listbox(
                        values=["All", "1", "2", "3"],
                        enable_events=True,
                        default_values=[
                            "All" if channel is None else channel,
                        ],
                        size=(30, 3),
                        key="channel",
                    )
                ],
                [sg.Button("Save", k="save"), sg.Exit()],
            ],
        ).read(close=True)
        new_color_mode = values["color_mode"][0]
        channel = values["channel"][0]
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event == "channel" or "color_mode":
            new_image = normalize(image, max_val)
            new_image = convert_color(new_image, "rgb", new_color_mode)
            new_image = to_8bit(new_image)
            buffer = io.BytesIO()
            if channel == "All":
                write_pnm(new_image, max_val, buffer)
            else:
                ch1, ch2, ch3 = np.moveaxis(new_image, -1, 0)
                if channel == "1":
                    write_pnm(ch1, max_val, buffer)
                if channel == "2":
                    write_pnm(ch2, max_val, buffer)
                if channel == "3":
                    write_pnm(ch3, max_val, buffer)

        if event == "save":
            event, values = sg.Window(
                "Save as", [[sg.Input(k="filename"), sg.SaveAs(target="filename")], [sg.Save()]]
            ).read(close=True)
            try:
                with open_pnm_file(values["filename"], "wb") as file:
                    file.write(buffer.getvalue())
            except Exception as exc:
                handle_exception(exc)
