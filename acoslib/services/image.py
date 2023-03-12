from __future__ import annotations

import pathlib
from abc import ABC, abstractmethod

from acoslib import services, types
from acoslib.utils import cmdlib


class _BaseImageService(services.AltcosService, ABC):

    @abstractmethod
    def mkimage(self, commit: types.Commit) -> _BaseImageService:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[types.Image]:
        raise NotImplementedError


class _QcowImageService(_BaseImageService):
    def mkimage(self, commit: types.Commit) -> _BaseImageService:
        cmdlib.runcmd(f"sudo -E {self.reference.repository.script_root}/cmd_make_qcow2.sh "
                      f"{self.reference} {commit.sha256}")
        return self

    def list(self) -> list[types.Image]:
        qcow_dir = pathlib.Path(self.reference.imagedir, types.ImageFmt.Qcow.value)

        if not qcow_dir.exists():
            raise FileNotFoundError(f"directory {qcow_dir} not found")

        img_list = []

        for img_path in qcow_dir.glob(f"*.{types.ImageFmt.Qcow.value}"):
            img_list.append(types.Image([types.ImageItem(img_path, types.ImageFmt.Qcow), ]))

        return img_list


class ImageService(services.AltcosService):
    _FACTORY_LIST = {
        types.ImageFmt.Qcow: _QcowImageService,
    }

    def __new__(cls, reference: types.Reference, image_fmt: types.ImageFmt) -> _BaseImageService:
        return cls._FACTORY_LIST.get(image_fmt)(reference)
