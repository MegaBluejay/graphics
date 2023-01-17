import io
import zlib
from contextlib import contextmanager
from enum import Enum
from math import floor
from time import sleep

import numpy as np

from graphics.pnm.exceptions import *

PNG_SIGNATURE = bytes(bytearray.fromhex("89 50 4E 47 0D 0A 1A 0A"))
ChunkType = Enum(
    "ChunkType",
    [
        "IHDR",
        "PLTE",
        "IDAT",
        "IEND",
        "bKGD",
        "cHRM",
        "gAMA",
        "hIST",
        "iCCP",
        "iTXt",
        "pHYs",
        "sBIT",
        "sPLT",
        "sRGB",
        "sTER",
        "tEXt",
        "tIME",
        "tRNS",
        "zTXt",
    ],
)

lookup_table = []


def create_table():
    for i in range(256):
        k = i
        for _ in range(8):
            k = (k >> 1) ^ 0xEDB88320 if k & 1 else k >> 1
        lookup_table.append(k & 0xFFFFFFFF)


def crc32(bytestream):
    if len(lookup_table) == 0:
        create_table()
    crc = 0xFFFFFFFF
    for byte in bytestream:
        lookup_index = (crc ^ byte) & 0xFF
        crc = ((crc >> 8) & 0xFFFFFFFF) ^ lookup_table[lookup_index]
    return crc ^ 0xFFFFFFFF


class Chunk:
    def __init__(self, chunk_type: ChunkType, data: bytes):
        self.chunk_type = chunk_type
        self.data = data

    def create_binary(self):
        data = bytearray()
        length = len(self.data).to_bytes(4, "big")
        data += length
        chunk_type = self.chunk_type.name.encode("utf-8")
        data += chunk_type
        data += self.data
        checksum_data = bytearray(chunk_type)
        checksum_data += self.data
        data += crc32(bytearray(checksum_data)).to_bytes(4, "big")
        return data


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
        for c in range(width * bytes_per_pixel):  # for each byte in scanline
            curr = data[i]
            i += 1
            raw_x_bpp = image[r * width * bytes_per_pixel + c - bytes_per_pixel] if c >= bytes_per_pixel else 0
            prior_x = image[(r - 1) * width * bytes_per_pixel + c] if r > 0 else 0
            prior_x_bpp = (
                image[(r - 1) * width * bytes_per_pixel + c - bytes_per_pixel] if r > 0 and c >= bytes_per_pixel else 0
            )
            if filter_type == 0:  # None
                image.append(curr)
            elif filter_type == 1:  # Sub
                image.append((curr + raw_x_bpp) & 0xFF)
            elif filter_type == 2:  # Up
                image.append((curr + prior_x) & 0xFF)
            elif filter_type == 3:  # Average
                image.append((curr + (raw_x_bpp + prior_x) // 2) & 0xFF)
            elif filter_type == 4:  # Paeth
                image.append((curr + paeth_predictor(raw_x_bpp, prior_x, prior_x_bpp)) & 0xFF)
            else:
                raise Exception("unknown filter type: " + str(filter_type))
    return image


def filter(data, filter_type: int):
    image = []
    i = 0
    height, width = data.shape[:2]
    bytes_per_pixel = 3 if data.ndim == 3 else 1
    data = list(data.ravel())
    for r in range(height):  # for each scanline
        image.append(filter_type)
        for c in range(width * bytes_per_pixel):  # for each byte in scanline
            curr = data[i]
            i += 1
            raw_x_bpp = data[r * width * bytes_per_pixel + c - bytes_per_pixel] if c >= bytes_per_pixel else 0
            prior_x = data[(r - 1) * width * bytes_per_pixel + c] if r > 0 else 0
            prior_x_bpp = (
                data[(r - 1) * width * bytes_per_pixel + c - bytes_per_pixel] if r > 0 and c >= bytes_per_pixel else 0
            )
            if filter_type == 0:  # None
                image.append(curr)
            # BUG
            elif filter_type == 1:  # Sub
                image.append((curr - raw_x_bpp) & 0xFF)
            elif filter_type == 2:  # Up
                image.append((curr - prior_x) & 0xFF)
            elif filter_type == 3:  # Average
                image.append((curr - (raw_x_bpp + prior_x) // 2) & 0xFF)
            elif filter_type == 4:  # Paeth
                image.append((curr - paeth_predictor(raw_x_bpp, prior_x, prior_x_bpp)) & 0xFF)
            else:
                raise Exception("unknown filter type: " + str(filter_type))
    return image


def apply_palette(image, palette):
    if len(bytearray(palette)) % 3 != 0:
        raise InvalidContent("PLTE", palette)
    palette = np.array(bytearray(palette)).reshape(len(bytearray(palette)) // 3, 3)
    converted_img = np.array([palette[pixel] for pixel in image])
    return converted_img


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

    idat = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == ChunkType.IDAT)
    decoded = zlib.decompress(idat)
    image = defilter(decoded, width, height, bytes_per_pixel)
    if color_type == 3:
        palette = next(chunk for chunk in chunks if chunk.chunk_type == ChunkType.PLTE)
        image = apply_palette(image, palette.data)
        image = np.array(image).reshape(height, width, 3)
    elif color_type == 2:
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
        name = reader.read(4).decode("ascii")
        content = reader.read(len)
        _checksum = reader.read(4)
        if name == "":
            if any([chunk.chunk_type == ChunkType.IEND for chunk in chunks]):
                break
            else:
                raise ChunkNotFound("IEND")
        chunks.append(build_chunk(name, content))

    gamma = next((chunk for chunk in chunks if chunk.chunk_type == ChunkType.gAMA), None)
    if gamma is None:
        gamma = 2.2
    else:
        gamma = float(int.from_bytes(gamma.data, "big")) / 100000
    sRgb = next((chunk for chunk in chunks if chunk.chunk_type == ChunkType.sRGB), None)
    if sRgb is not None:
        gamma = 2.2
    return build_image(chunks), gamma


def write_png(image, file, gamma, filter_type=4):
    # Построение IHDR
    chunks = []
    ihdr_data = bytearray()
    height, width = image.shape[:2]
    ihdr_data += width.to_bytes(4, "big")
    ihdr_data += height.to_bytes(4, "big")
    ihdr_data += bytes(b"\x08")
    color_type = bytes(b"\x00")
    if image.ndim == 3:
        color_type = bytes(b"\x02")
    ihdr_data += color_type
    ihdr_data += bytes(b"\x00\x00\x00")
    IHDR = Chunk(ChunkType.IHDR, ihdr_data)
    chunks.append(IHDR)

    gAMA = Chunk(ChunkType.gAMA, floor(gamma * 100_000).to_bytes(4, "big"))
    chunks.append(gAMA)

    # Построение IDAT
    filtered = filter(image, filter_type)
    filtered = b"".join(int(byte).to_bytes(1, "big") for byte in filtered)
    compressed = zlib.compress(filtered)
    compressed_splitted = []
    for i in range(0, len(compressed), 8192):
        compressed_splitted.append(compressed[i : i + 8192])

    for idat_data in compressed_splitted:
        IDAT = Chunk(ChunkType.IDAT, idat_data)
        chunks.append(IDAT)
    IEND = Chunk(ChunkType.IEND, b"")
    chunks.append(IEND)
    file.write(PNG_SIGNATURE)
    for chunk in chunks:
        file.write(chunk.create_binary())
