import numpy as np


def normalize(image, max_val):
    return image.astype(float) / max_val


def to_8bit(image):
    return np.round(image * 255).astype("u1")
