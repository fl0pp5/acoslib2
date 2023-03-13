from __future__ import annotations

import abc
import os
import pathlib

from acoslib import models
from acoslib.types import ImageFormat
from acoslib.utils import cmdlib


class ImageItem:
    __slots__ = (
        "_location",
        "_format",
    )

    def __init__(self, location: str | os.PathLike, img_format: models.ImageFormat) -> None:
        self._location = pathlib.Path(location)
        self._format = img_format

        if not self._location.exists():
            raise FileExistsError(f"image item {self._location} not exists")

    @property
    def location(self) -> pathlib.Path:
        return self._location

    @property
    def format(self) -> ImageFormat:
        return self._format


class BaseImage(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, reference: models.Reference, commit_id: str) -> BaseImage:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def all(cls, reference: models.Reference) -> list[BaseImage]:
        raise NotImplementedError

    @abc.abstractmethod
    def items(self) -> dict[str, ImageItem]:
        raise NotImplementedError


class QcowImage(BaseImage):

    __slots__ = (
        "_disk",
    )

    def __init__(self, disk: ImageItem) -> None:
        self._disk = disk

    @classmethod
    def create(cls, reference: models.Reference, commit_id: str) -> BaseImage:
        cmdlib.runcmd(
            cmd=f"sudo -E {reference.altcos_paths.script_root}/cmd_make_qcow2.sh {reference} {commit_id}")
        return QcowImage.all(reference)[-1]

    @classmethod
    def all(cls, reference: models.Reference) -> list[BaseImage]:
        qcow_dir = pathlib.Path(reference.imagedir, ImageFormat.QCOW.value)

        if not qcow_dir.exists():
            raise FileNotFoundError(f"directory {qcow_dir} not found")

        img_list = []

        for img in qcow_dir.glob(f"*.{ImageFormat.QCOW.value}"):
            img_list.append(QcowImage(ImageItem(img, ImageFormat.QCOW)))

        return img_list

    def items(self) -> dict[str, ImageItem]:
        return {"disk": self._disk}
