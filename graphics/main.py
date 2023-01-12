import io

import numpy as np
import PySimpleGUI as sg

from .colors import Image, color_modes
from .dither import algos
from .draw import draw_line
from .histo import correct, histo
from .png import read_png, write_png
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
image = None
image_data = None
h = 0
w = 0
with handle_exception(exit_on_error=True):
    with open_pnm_file(filename, "rb") as file:
        if str(filename).split(".")[-1] != "png":
            image_data, max_val = read_pnm(file)
            h, w = image_data.shape[:2]
            image_data = normalize(image_data, max_val)
            image = Image(image_data, color_mode)
        else:
            image_data, gamma = read_png(file)
            h, w = image_data.shape[:2]
            image = Image(normalize(image_data, 255), color_mode, gamma)

channel = "All"
layout = [
    [
        sg.Graph((w, h), (0, h - 1), (w - 1, 0), key="graph", enable_events=True, drag_submits=True),
        sg.Column(
            [
                [sg.Input("0.5", key=("line_color", i), size=(5, 1)) for i in range(3)],
                [sg.Text("Line Width"), sg.Input("1", key="line_width", size=(5, 1))],
                [sg.Text("Line alpha"), sg.Input("0.5", key="line_alpha", size=(5, 1))],
            ],
        ),
    ],
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
                [sg.Input(str(image.gamma), size=(5, 1), key="gamma")],
                [sg.Button("Convert Gamma", key="convert_gamma")],
                [sg.Button("Assign Gamma", key="assign_gamma")],
            ],
        ),
        sg.Column(
            [
                [sg.Text("Bitness"), sg.Input("8", size=(5, 1), key="bitness")],
                [
                    sg.Listbox(
                        values=list(algos.keys()),
                        default_values=["ordered"],
                        enable_events=True,
                        size=(15, 5),
                        key="dither_algo",
                    )
                ],
                [sg.Button("Dither", key="dither")],
                [sg.Button("Gradient", key="gradient")],
            ],
        ),
        sg.Column(
            [
                [sg.Button("Histogram", key="histo")],
            ],
        ),
    ],
    [sg.Button("Save", key="save"), sg.Exit()],
]

window = sg.Window("PNM", layout, finalize=True, element_justification="center")
draw_image(window["graph"], image, color_mode, channel)
p0, og_image = None, None
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
        if event == "graph":
            if p0 is not None:
                if values["graph"] != p0:
                    line = draw_line((h, w), np.array(p0), np.array(values["graph"]), int(values["line_width"]))
                    color = np.array([float(values[("line_color", i)]) for i in range(3)])
                    alpha = float(values["line_alpha"]) * line
                    image_data = og_image[color_mode].copy()
                    if channel == "All":
                        image_data = alpha[:, :, np.newaxis] * color + (1 - alpha[:, :, np.newaxis]) * image_data
                    else:
                        i = int(channel) - 1
                        image_data[:, :, i] = alpha * color[i] + (1 - alpha) * image_data[:, :, i]
                    image = Image(image_data, color_mode, gamma=og_image.gamma)
            else:
                p0, og_image = values["graph"], image
        if event == "graph+UP":
            p0, og_image = None, None
        if event == "dither":
            try:
                algo = algos[values["dither_algo"][0]]
                bitness = int(values["bitness"])
                image = Image(algo(image.convert_gamma(1)["rgb"], bitness), gamma=1).convert_gamma(image.gamma)
            except ValueError:
                window["bitness"].update("8")
        if event == "gradient":
            image = Image(np.tile(np.linspace((0, 0, 0), (1, 1, 1), 256), (256, 1, 1)), gamma=image.gamma)
        if event == "histo":
            image_data = image[color_mode]
            if channel != "All":
                image_data = image_data[int(channel) - 1]
            histo_graph = histo(image_data)
            buffer = io.BytesIO()
            write_pnm(to_8bit(histo_graph), 255, buffer)
            histo_event, histo_values = sg.Window(
                "Histogram",
                [
                    [sg.Image(data=buffer.getvalue())],
                    [sg.Text("Ignore"), sg.Input("0", key="ignore")],
                    [sg.Ok(), sg.Button("Correct", key="correct")],
                ],
            ).read(close=True)
            if histo_event == "correct":
                ignore = float(histo_values["ignore"])
                image_data = correct(image_data, ignore)
                if channel != "All":
                    all_data = image[color_mode]
                    all_data[int(channel) - 1] = image_data
                else:
                    all_data = image_data
                image = Image(all_data, color_mode=color_mode, gamma=image.gamma)
        if event in [
            "color_mode",
            "channel",
            "assign_gamma",
            "convert_gamma",
            "graph",
            "dither",
            "gradient",
            "histogram",
        ]:
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
                        if str(filename).split(".")[-1] != "png":
                            write_pnm(to_8bit(image.convert_gamma(2.2)[color_mode]), 255, file)
                        else:
                            write_png(to_8bit(image.convert_gamma(2.2)[color_mode]).astype(int), file, 2.2)
