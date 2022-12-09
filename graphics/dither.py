from functools import cache, partial
from itertools import product
from math import ceil

import numpy as np

rng = np.random.default_rng()


def closest(c):
    q = np.array([np.floor(c), np.ceil(c)]).T
    lats = np.array(list(product(*q)), dtype=float)
    dists = np.sum((lats - c[np.newaxis, :]) ** 2, axis=1)
    return lats[np.argmin(dists)]


@cache
def ordered_tile(pow2, pre=True):
    if pow2 == 0:
        return 0
    prev = ordered_tile(pow2 - 1, pre=False)
    q = 2 ** (2 * pow2)
    res = np.block([[prev, prev + 2 / q], [prev + 3 / q, prev + 1 / q]])
    if pre:
        res -= 0.5
    return res


def ordered_dither(image, bitness):
    h, w = image.shape[:2]
    q = 2**bitness - 1
    tile_map = np.tile(ordered_tile(3), (ceil(h / 8), ceil(w / 8)))[:h, :w]
    return np.round(image * q + tile_map[:, :, np.newaxis]) / q


def random_dither(image, bitness, sync_channels):
    q = 2**bitness - 1
    if sync_channels:
        random_map = rng.random(size=image.shape[:2])[:, :, np.newaxis] - 0.5
    else:
        random_map = rng.random(size=image.shape) - 0.5
    return np.round(image * q + random_map) / q


def floyd_dither(image, bitness):
    q = 2**bitness - 1
    image *= q
    h, w = image.shape[:2]
    ww = np.zeros((h + 1, w + 1, 3))
    for i in range(h):
        for j in range(w):
            new = np.clip(np.round(image[i, j] + ww[i, j]), 0, q)
            err = (image[i, j] + ww[i, j] - new) / 16
            image[i, j] = new
            ww[i, j + 1] += err * 7
            ww[i + 1, j - 1] += err * 3
            ww[i + 1, j] += err * 5
            ww[i + 1, j + 1] += err
    return image / q


def atkinson_dither(image, bitness):
    q = 2**bitness - 1
    image *= q
    h, w = image.shape[:2]
    ww = np.zeros((h + 2, w + 2, 3))
    for i in range(h):
        for j in range(w):
            new = np.clip(np.round(image[i, j] + ww[i, j]), 0, q)
            err = (image[i, j] + ww[i, j] - new) / 8
            image[i, j] = new
            for (di, dj) in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                ww[i + di, j + dj] += err
    return image / q


algos = {
    "ordered": ordered_dither,
    "random_sync": partial(random_dither, sync_channels=True),
    "random_nosync": partial(random_dither, sync_channels=False),
    "floyd": floyd_dither,
    "atkinson": atkinson_dither,
}
