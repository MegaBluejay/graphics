from functools import wraps

import numpy as np

color_modes = ["rgb", "hsl", "hsv", "ypbpr601", "ypbpr709", "ycocg", "cmy"]


def get_h(image, c_max, c_delta, out):
    has_delta = c_delta != 0
    rmax = has_delta & (c_max == image[:, :, 0])
    out[rmax] = (image[rmax, 1] - image[rmax, 2]) / c_delta[rmax]
    gmax = has_delta & (c_max == image[:, :, 1])
    out[gmax] = (image[gmax, 2] - image[gmax, 0]) / c_delta[gmax] + 2
    bmax = has_delta & (c_max == image[:, :, 2])
    out[bmax] = (image[bmax, 0] - image[bmax, 1]) / c_delta[bmax] + 4
    out /= 6
    out %= 1


def get_sl(c_max, c_sum, c_delta, out):
    out[:, :, 1] = l = c_sum / 2
    ok = (l != 0) & (l != 1)
    out[ok, 0] = c_delta[ok] / (1 - np.abs(c_sum[ok] - 1))


def get_sv(c_max, c_sum, c_delta, out):
    out[:, :, 1] = v = c_max
    ok = v != 0
    out[ok, 0] = c_delta[ok] / v[ok]


def rgb_to_hsx(get_sx):
    def convert(image):
        new = np.zeros_like(image)
        c_min, c_max = image.min(axis=2), image.max(axis=2)
        c_sum, c_delta = c_max + c_min, c_max - c_min
        get_h(image, c_max, c_delta, new[:, :, 0])
        get_sx(c_max, c_sum, c_delta, new[:, :, 1:])
        return new

    return convert


def hsl_to_rgb(image):
    new = np.zeros_like(image)
    alpha = image[:, :, 1] * np.minimum(image[:, :, 2], 1 - image[:, :, 2])
    for i, n in enumerate([0, 8, 4]):
        k = (n + image[:, :, 0] * 12) % 12
        new[:, :, i] = image[:, :, 2] - alpha * np.maximum(-1, np.minimum(k - 3, np.minimum(9 - k, 1)))
    return new


def hsv_to_rgb(image):
    new = np.zeros_like(image)
    for i, n in enumerate([5, 3, 1]):
        k = (n + image[:, :, 0] * 6) % 6
        new[:, :, i] = image[:, :, 2] * (1 - image[:, :, 1] * np.maximum(0, np.minimum(k, np.minimum(4 - k, 1))))
    return new


def mul_colors(mat, image):
    return np.einsum("ij,mnj->mni", mat, image)


def make_ypbpr(kr, kg, kb):
    there_mat = np.array(
        [
            [kr, kg, kb],
            [-kr / 2 / (1 - kb), -kg / 2 / (1 - kb), 1 / 2],
            [1 / 2, -kg / 2 / (1 - kr), -kb / 2 / (1 - kr)],
        ]
    )
    back_mat = np.linalg.inv(there_mat)

    def there(image):
        return mul_colors(there_mat, image)

    def back(image):
        return mul_colors(back_mat, image)

    return there, back


rgb_to_ypbpr601, ypbpr601_to_rgb = make_ypbpr(0.299, 0.587, 0.114)
rgb_to_ypbpr709, ypbpr709_to_rgb = make_ypbpr(0.2126, 0.7152, 0.0722)

ycocg_there_mat = np.array(
    [
        [1 / 4, 1 / 2, 1 / 4],
        [1 / 2, 0, -1 / 2],
        [-1 / 4, 1 / 2, -1 / 4],
    ]
)
ycocg_back_mat = np.linalg.inv(ycocg_there_mat)


def rgb_to_ycocg(image):
    return mul_colors(ycocg_there_mat, image)


def ycocg_to_rgb(image):
    return mul_colors(ycocg_back_mat, image)


def cmy(rgb):
    return 1 - rgb


rgb_to = {
    "hsl": rgb_to_hsx(get_sl),
    "hsv": rgb_to_hsx(get_sv),
    "ypbpr601": rgb_to_ypbpr601,
    "ypbpr709": rgb_to_ypbpr709,
    "ycocg": rgb_to_ycocg,
    "cmy": cmy,
}

to_rgb = {
    "hsl": hsl_to_rgb,
    "hsv": hsv_to_rgb,
    "ypbpr601": ypbpr601_to_rgb,
    "ypbpr709": ypbpr709_to_rgb,
    "ycocg": ycocg_to_rgb,
    "cmy": cmy,
}


def convert_color(image, frm, to):
    if frm != "rgb":
        image = to_rgb[frm](image)
    if to != "rgb":
        image = rgb_to[to](image)
    return image


class Image:
    def __init__(self, data, color_mode="rgb", gamma=2.2, parent=None):
        self.data = data
        self.color_mode = color_mode
        self.gamma = gamma
        self.cache = {color_mode: data}
        self.gamma_cache = parent.gamma_cache if parent else {}
        self.gamma_cache[gamma] = self

    def __getitem__(self, color_mode):
        if color_mode not in self.cache:
            self.cache[color_mode] = convert_color(self.data, self.color_mode, color_mode)
            if color_mode == "rgb":
                self.color_mode = "rgb"
        return self.cache[color_mode]

    def convert_gamma(self, gamma):
        if gamma not in self.gamma_cache:
            return Image(self["rgb"] ** (self.gamma / gamma), gamma=gamma, parent=self)
        return self.gamma_cache[gamma]

    def assign_gamma(self, gamma):
        self.gamma = gamma
        self.gamma_cache = {gamma: self}
