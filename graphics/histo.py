import numpy as np


def histo(image):
    vals = np.round(255 * np.histogram(image, bins=256, range=(0, 1), density=True)[0]).astype(int)
    graph = np.ones((256, 256))
    for i, val in enumerate(vals):
        graph[255 - val :, i] = 0
    return graph


def correct(image: np.ndarray, ignore):
    k = round(image.size * ignore)
    inds = np.argpartition(image, kth=[k, image.size - 1 - k], axis=None)[k : image.size - k]
    normal_vals = np.take(image, inds)
    mn, mx = np.amin(normal_vals), np.amax(normal_vals)
    if mn == mx:
        return image
    return np.clip((image - mn) / (mx - mn), 0, 1)
