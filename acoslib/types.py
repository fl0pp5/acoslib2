import enum


class Arch(enum.Enum):
    X86_64 = "x86_64"


class Stream(enum.Enum):
    SISYPHUS = "sisyphus"
    P10 = "p10"


class ImageFormat(enum.Enum):
    QCOW = "qcow2"
    ISO = "iso"
