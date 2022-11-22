from itertools import tee

import numpy as np
from numpy.lib.stride_tricks import as_strided


def normalize(image, max_val):
    return image.astype(float) / max_val


def to_8bit(image):
    return np.round(image * 255).astype("u1")


def pairwise(it):
    a, b = tee(iter(it))
    next(b, None)
    return zip(a, b)


def blockwise_view(a, block_shape):
    outer_shape = tuple(np.array(a.shape) // block_shape)
    view_shape = outer_shape + block_shape
    inner_strides = a.strides
    outer_strides = tuple(a.strides * np.array(block_shape))
    return as_strided(a, shape=view_shape, strides=outer_strides + inner_strides)
