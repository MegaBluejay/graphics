from itertools import chain
from math import ceil, floor

import numpy as np

from .utils import blockwise_view, pairwise


def inter(y, p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return x1 + (x2 - x1) * (y - y1) / (y2 - y1)


def draw_rect(im_shape, ps):
    im_shape = np.array(im_shape)
    big_im = np.zeros(im_shape * 4)
    ps = ps * 4 - 2
    lines = list(pairwise(chain(ps, ps[:1])))
    pi, (_, miny) = min(enumerate(ps), key=lambda q: q[1][1])
    li1, li2 = (pi - 1) % 4, pi
    y = ceil(miny)
    if ceil(ps[(pi + 1) % 4][1]) == y:
        big_im[y : floor(ps[(pi + 2) % 4][1]) + 1, ceil(ps[pi][0]) : floor(ps[(pi + 1) % 4][0]) + 1] = 1
        return blockwise_view(big_im, (4, 4)).sum(axis=(2, 3)) / 16
    sides = 0
    while True:
        if y > lines[li1][0][1]:
            li1 = (li1 - 1) % 4
            sides += 1
        if y > lines[li2][1][1]:
            li2 = (li2 + 1) % 4
            sides += 1
        if sides == 4:
            return blockwise_view(big_im, (4, 4)).sum(axis=(2, 3)) / 16
        x1, x2 = inter(y, *lines[li1]), inter(y, *lines[li2])
        big_im[y, ceil(x1) : floor(x2)] = 1
        y += 1


def draw_line(im_shape, p1, p2, width):
    h = p2 - p1
    w_half = width * np.array([[0, 1], [-1, 0]]) @ h / np.linalg.norm(h)
    ps = np.array([p1 + w_half, p2 + w_half, p2 - w_half, p1 - w_half])
    for i in range(2):
        np.clip(ps[:, i], 0, im_shape[i] - 1, ps[:, i])
    return draw_rect(im_shape, ps)
