from functools import wraps

import numpy as np


def with_array(func):
    @wraps(func)
    def wrapper(arr):
        return np.array(func(*arr))

    return wrapper


def get_h(r, g, b, c_max, c_delta):
    if c_max == r:
        h = (g - b) / c_delta
    elif c_max == g:
        h = (b - r) / c_delta + 2
    else:
        h = (r - g) / c_delta + 4
    return (h / 6) % 1


def get_sl(c_max, c_sum, c_delta):
    l = c_sum / 2
    if l in [0, 1]:
        s = 0
    else:
        s = c_delta / (1 - abs(c_sum - 1))
    return s, l


def get_sv(c_max, c_sum, c_delta):
    v = c_max
    if v == 0:
        s = 0
    else:
        s = c_delta / v
    return s, v


def rgb_to_hsx(get_sx):
    @with_array
    def convert(r, g, b):
        c_min, c_max = min(r, g, b), max(r, g, b)
        c_sum, c_delta = c_max + c_min, c_max - c_min
        h = get_h(r, g, b, c_max, c_delta)
        s, x = get_sx(c_max, c_sum, c_delta)
        return h, s, x

    return convert


rgb_to_hsl = rgb_to_hsx(get_sl)
rgb_to_hsv = rgb_to_hsx(get_sv)


@with_array
def hsl_to_rgb(h, s, l):
    rgb = []
    alpha = s * min(l, 1 - l)
    for n in (0, 8, 4):
        k = (n + h * 12) % 12
        rgb.append(l - alpha * max(-1, min(k - 3, 9 - k, 1)))
    return rgb


@with_array
def hsv_to_rgb(h, s, v):
    rgb = []
    for n in (5, 3, 1):
        k = (n + h * 6) % 6
        rgb.append(v * (1 - s * max(0, min(k, 4 - k, 1))))
    return rgb