import PySimpleGUI as sg

from .colors import Image, color_modes
from .pnm import open_pnm_file, read_pnm, write_pnm
from .ui_utils import draw_image, handle_exception, open_window, require_filename
from .utils import normalize, to_8bit

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

channel = "All"
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
        sg.Column(
            [
                [sg.Input("2.2", size=(5, 1), key="gamma")],
                [sg.Button("Convert Gamma", key="convert_gamma")],
                [sg.Button("Assign Gamma", key="assign_gamma")],
            ],
        ),
    ],
    [sg.Button("Save", key="save"), sg.Exit()],
]

window = sg.Window("PNM", layout, finalize=True, element_justification="center")
draw_image(window["graph"], image, color_mode, channel)
with open_window(window) as evs:
    for event, values in evs:
        if event == "color_mode":
            color_mode = values["color_mode"][0]
            window["channel"].update(set_to_index=0)
            channel = "All"
        if event == "channel":
            channel = values["channel"][0]
        if event in ["assign_gamma", "convert_gamma"]:
            try:
                gamma = float(values["gamma"])
            except ValueError:
                window["gamma"].update(str(image.gamma))
            else:
                if event == "convert_gamma":
                    image = image.convert_gamma(gamma)
                if event == "assign_gamma":
                    image.assign_gamma(gamma)
        if event in ["color_mode", "channel", "assign_gamma", "convert_gamma"]:
            draw_image(window["graph"], image, color_mode, channel)
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
                        write_pnm(to_8bit(image.convert_gamma(2.2)[color_mode]), 255, file)
