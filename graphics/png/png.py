from contextlib import contextmanager
from enum import Enum
import io

import numpy as np

from graphics.pnm.exceptions import *
from time import sleep
import zlib

PNG_SIGNATURE = bytes(bytearray.fromhex("89 50 4E 47 0D 0A 1A 0A"))
ChunkType = Enum('ChunkType',
                 ['IHDR', 'PLTE', 'IDAT', 'IEND', 'bKGD', 'cHRM', 'gAMA', 'hIST', 'iCCP', 'iTXt', 'pHYs', 'sBIT',
                  'sPLT', 'sRGB', 'sTER', 'tEXt', 'tIME', 'tRNS', 'zTXt'])


class Chunk:
    def __init__(self, chunk_type: ChunkType, data:bytes):
        self.chunk_type = chunk_type
        self.data = data


def build_chunk(name, content):
    if name not in dir(ChunkType):
        raise UnknownChunkType(name)
    return Chunk(ChunkType[name], content)


def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c


def defilter(data, width, height, bytes_per_pixel):
    image = []
    i = 0
    for r in range(height):  # for each scanline
        filter_type = data[i]  # first byte of scanline is filter type
        i += 1
        for c in range(width*bytes_per_pixel):  # for each byte in scanline
            curr = data[i]
            i += 1
            raw_x_bpp = (image[r * width * bytes_per_pixel + c - bytes_per_pixel] if c >= bytes_per_pixel else 0)
            prior_x = (image[(r - 1) * width * bytes_per_pixel + c] if r > 0 else 0)
            prior_x_bpp = (image[(r-1) * width * bytes_per_pixel + c - bytes_per_pixel] if r > 0 and c >= bytes_per_pixel else 0)
            if filter_type == 0:  # None
                image.append(curr)
            elif filter_type == 1:  # Sub
                image.append((curr + raw_x_bpp) & 0xff)
            elif filter_type == 2:  # Up
                image.append((curr + prior_x) & 0xff)
            elif filter_type == 3:  # Average
                image.append((curr + (raw_x_bpp + prior_x) // 2) & 0xff)
            elif filter_type == 4:  # Paeth
                image.append((curr + paeth_predictor(raw_x_bpp, prior_x, prior_x_bpp)) & 0xff)
            else:
                raise Exception('unknown filter type: ' + str(filter_type))
    return image


def build_image(chunks: list[Chunk]):
    ihdr = next(chunk for chunk in chunks if chunk.chunk_type == ChunkType.IHDR)
    reader = io.BytesIO(ihdr.data)
    width = int.from_bytes(reader.read(4), "big")
    height = int.from_bytes(reader.read(4), "big")
    depth = int.from_bytes(reader.read(1), "big")
    color_type = int.from_bytes(reader.read(1), "big")
    deflate = int.from_bytes(reader.read(1), "big")
    filter = int.from_bytes(reader.read(1), "big")
    interlace = int.from_bytes(reader.read(1), "big")
    bytes_per_pixel = 3 if color_type == 2 else 1
    if width == 0 or height == 0 or depth != 8 or color_type == 4 or color_type == 6 or deflate != 0 or interlace != 0:
        InvalidContent("IHDR", ihdr.data)
    print(width, height, depth, color_type, filter)
    idat = b''.join(chunk.data for chunk in chunks if chunk.chunk_type == ChunkType.IDAT)
    decoded = zlib.decompress(idat)
    image = defilter(decoded, width, height, bytes_per_pixel)
    if color_type == 2:
        image = np.array(image).reshape(height, width, 3)
    else:
        image = np.array(image).reshape(height, width)
    return image



@contextmanager
def open_png_file(filename, *args, **kwargs):
    try:
        file = open(filename, *args, **kwargs)
    except IOError as e:
        raise FileOpenError(filename) from e
    try:
        yield file
    finally:
        file.close()


def read_png(file):
    reader = io.BufferedReader(file)
    sign = reader.read(8)
    # проверка подписи
    if sign != PNG_SIGNATURE:
        raise PngSignature(sign)
    # разбиение на чанки
    chunks = []
    while True:
        len = int.from_bytes(reader.read(4), "big")
        name = reader.read(4).decode('ascii')
        content = reader.read(len)
        _checksum = reader.read(4)
        if name == '':
            if any([chunk.chunk_type == ChunkType.IEND for chunk in chunks]):
                break
            else:
                raise ChunkNotFound("IEND")
        chunks.append(build_chunk(name, content))
        print(name)
    return build_image(chunks)
