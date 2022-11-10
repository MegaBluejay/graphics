from dataclasses import dataclass


class PnmError(Exception):
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
