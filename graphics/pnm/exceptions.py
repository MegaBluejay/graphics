from dataclasses import dataclass


class PnmError(Exception):
    pass


class PngError(Exception):
    pass


@dataclass
class FileOpenError(PnmError):
    filename: str


@dataclass
class UnknownTagError(PnmError):
    tag: bytes


@dataclass
class FormatError(PnmError):
    file_part: str


@dataclass
class DataError(PnmError):
    problem: str


@dataclass
class PngSignature(PngError):
    signature: str


@dataclass
class UnknownChunkType(PngError):
    chunk_name: str


@dataclass
class ChunkNotFound(PngError):
    chunk_name: str


@dataclass
class InvalidContent(PngError):
    chunk_name: str
    content: str
