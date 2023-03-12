from __future__ import annotations

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
RpmPackage = NewType("RpmPackage", str)
AltConf = NewType("AltConf", str)


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
    script_root: os.PathLike | str
    stream_root: os.PathLike | str
    mkp_root: os.PathLike | str


@dataclass
class Reference:
    repository: Repository
    osname: OSName
    arch: Arch
    branch: Branch
    stream: Stream = Stream("")

    def __str__(self) -> str:
        return str(pathlib.Path(self.osname.value,
                                self.arch.value,
                                self.branch.value.capitalize() if self.stream else self.branch.value,
                                self.stream))

    @property
    def basedir(self) -> pathlib.Path:
        return pathlib.Path(self.repository.stream_root,
                            self.osname.value,
                            self.arch.value,
                            self.branch.value)

    @property
    def refdir(self) -> pathlib.Path:
        return self.basedir.joinpath(self.stream)

    @property
    def repodir(self) -> pathlib.Path:
        return self.basedir.joinpath("bare", "repo")

    @property
    def imagedir(self) -> pathlib.Path:
        return self.refdir.joinpath("images")

    @property
    def mergedir(self) -> pathlib.Path:
        return self.refdir.joinpath("merged")

    @property
    def mkpdir(self) -> pathlib.Path:
        return self.basedir.joinpath("mkimage-profiles")

    @property
    def baseref(self) -> Reference:
        return Reference(self.repository, self.osname, self.arch, self.branch)


@dataclass
class OSTreeCommit:
    sha256: str
    version: Version
    date: datetime
    parent_id: str
