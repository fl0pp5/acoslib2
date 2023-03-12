import enum
import os
import pathlib
from typing import NewType
from dataclasses import dataclass
from datetime import datetime


class OSName(enum.Enum):
    Altcos = "altcos"


class Arch(enum.Enum):
    X86_64 = "x86_64"


class Branch(enum.Enum):
    Sisyphus = "sisyphus"
    P10 = "p10"


Stream = NewType("Stream", str)


@dataclass
class Version:
    stream: Stream
    date: str
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.stream}.{self.date}.{self.major}.{self.minor}"


@dataclass
class Repository:
    osname: OSName
    script_root: os.PathLike | str
    stream_root: os.PathLike | str
    mkp_root: os.PathLike | str


@dataclass
class Reference:
    repository: Repository
    arch: Arch
    branch: Branch
    stream: Stream = Stream("")


@dataclass
class OSTreeReference:
    osname: OSName
    arch: Arch
    branch: Branch
    stream: Stream = Stream("")

    def __str__(self) -> str:
        return str(pathlib.Path(self.osname.value,
                                self.arch.value,
                                self.branch.value,
                                self.stream))


@dataclass
class OSTreeCommit:
    sha256: str
    version: Version
    date: datetime
    parent_id: str


