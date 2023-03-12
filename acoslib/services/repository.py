import pathlib

from acoslib import types
from acoslib import services


class _OSTreeInfoService(services.BaseService):
    @property
    def ref(self) -> types.OSTreeReference:
        return types.OSTreeReference(self._reference.repository.osname,
                                     self._reference.arch,
                                     self._reference.branch,
                                     self._reference.stream)

    @property
    def baseref(self) -> types.OSTreeReference:
        return types.OSTreeReference(self._reference.repository.osname,
                                     self._reference.arch,
                                     self._reference.branch)


class _AltcosInfoService(services.BaseService):
    @property
    def refdir(self) -> pathlib.Path:
        return pathlib.Path(self._reference.repository.stream_root,
                            self._reference.repository.osname.value,
                            self._reference.arch.value,
                            self._reference.branch.value,
                            self._reference.stream)

    @property
    def basedir(self) -> pathlib.Path:
        return pathlib.Path(self._reference.repository.stream_root,
                            self._reference.repository.osname.value,
                            self._reference.arch.value,
                            self._reference.branch.value)

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


class RepositoryService(services.BaseService):
    """
    Service for getting info about altcos and ostree repository paths/refs by `types.Reference`
    """
    __slots__ = (
        "_ostree",
        "_altcos",
    )

    def __init__(self, reference: types.Reference) -> None:
        super().__init__(reference)
        self._ostree = _OSTreeInfoService(self._reference)
        self._altcos = _AltcosInfoService(self._reference)

    @property
    def ostree(self) -> _OSTreeInfoService:
        return self._ostree

    @property
    def altcos(self) -> _AltcosInfoService:
        return self._altcos
