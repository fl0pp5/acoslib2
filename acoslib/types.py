from __future__ import annotations

import enum


class Arch(enum.Enum):
    X86_64 = "x86_64"


class Stream(enum.Enum):
    SISYPHUS = "sisyphus"
    P10 = "p10"


class ImageFormat(enum.Enum):
    QCOW = "qcow2"
    ISO = "iso"


class Version:
    __slots__ = (
        "_name",
        "_date",
        "_major",
        "_minor",
    )

    def __init__(self, name: str, date: str, major: int, minor: int) -> None:
        self._name = name
        self._date = date
        self._major = int(major)
        self._minor = int(minor)

    def __str__(self) -> str:
        return f"{self._name}.{self._date}.{self._major}.{self._minor}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def date(self) -> str:
        return self._date

    @property
    def major(self) -> int:
        return self._major

    @major.setter
    def major(self, new: int) -> None:
        self._major = new

    @property
    def minor(self) -> int:
        return self._minor

    @minor.setter
    def minor(self, new: int) -> None:
        self._minor = new

    @classmethod
    def from_str(cls, version: str) -> Version:
        return cls(*version.split("."))
