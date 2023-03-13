from __future__ import annotations

import dataclasses
import enum
import os
import typing
from datetime import datetime


class OSName(enum.Enum):
    ALTCOS = "altcos"


class Arch(enum.Enum):
    X86_64 = "x86_64"


class Branch(enum.Enum):
    SISYPHUS = "sisyphus"
    P10 = "p10"


Stream = typing.NewType("Stream", str)
PkgName = typing.NewType("PkgName", str)


class ImageFormat(enum.Enum):
    QCOW = "qcow2"
    ISO = "iso"


@dataclasses.dataclass
class AltcosRepoPaths:
    script_root: os.PathLike | str
    stream_root: os.PathLike | str
    mkp_roto: os.PathLike | str


@dataclasses.dataclass
class Version:
    name: str
    date: str
    major: int
    minor: int

    @classmethod
    def from_str(cls, version: str) -> Version:
        return cls(*version.split("."))


@dataclasses.dataclass
class Commit:
    sha256: str
    version: Version
    date: datetime
    parent_id: str
