import io
import traceback

import PySimpleGUI as sg

from .pnm import open_pnm_file, read_pnm, write_pnm
from .pnm.exceptions import *


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
    [[sg.Text("Filename")], [sg.Input(k="filename"), sg.FileBrowse(target="filename")], [sg.OK(), sg.Cancel()]],
).read(close=True)
if event != "OK":
    exit()
filename = values["filename"]
buffer = io.BytesIO()
try:
    with open_pnm_file(filename, "rb") as file:
        image, max_val = read_pnm(file)
    write_pnm(image, max_val, buffer)
except Exception as exc:
    handle_exception(exc)
else:
    event, values = sg.Window(
        "PNP", [[sg.Image(data=buffer.getvalue())], [sg.Button("Save", k="save"), sg.Exit()]]
    ).read(close=True)
    if event == "save":
        event, values = sg.Window(
            "Save as", [[sg.Input(k="filename"), sg.SaveAs(target="filename")], [sg.Save()]]
        ).read(close=True)
        try:
            with open_pnm_file(values["filename"], "wb") as file:
                file.write(buffer.getvalue())
        except Exception as exc:
            handle_exception(exc)
