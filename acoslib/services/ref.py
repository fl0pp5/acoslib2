from __future__ import annotations

from acoslib import services, types
from acoslib.utils import cmdlib
from abc import ABC, abstractmethod


class _BaseReferenceService(services.BaseService, ABC):
    def clear_roots(self) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_clear_roots.sh "
                      f"{self.reference}")
        return self

    def update(self) -> _BaseReferenceService:
        last_commit = services.CommitService(self.reference).list()[-1]

        services.CommitService(self.clear_roots().reference).checkout(last_commit)

        services.AptService(self.reference).update().upgrade().update_kernel()

        last_commit.version.major += 1

        services.CommitService(self.reference).sync(last_commit).commit(last_commit)

        return self

    @abstractmethod
    def mkref(self) -> _BaseReferenceService:
        pass


class _MainReferenceService(_BaseReferenceService):
    def mkref(self) -> _BaseReferenceService:
        return self.mkrepo()

    def mkrepo(self) -> _MainReferenceService:
        cmdlib.runcmd(f"sudo -E {self.reference.repository.script_root}/cmd_rootfs2repo.sh "
                      f"{self.reference}")
        return self


class _SubReferenceService(_BaseReferenceService):
    def mkref(self) -> _BaseReferenceService:
        last_parent_commit = services.CommitService(self.reference.baseref).list()[-1]

        services.CommitService(self.reference).checkout(last_parent_commit)

        services.AltConfService(self.reference).exec(types.AltConf("altcos.yml"))

        services.CommitService(self.reference).sync(last_parent_commit).commit(last_parent_commit)

        return self


class ReferenceService(services.BaseService):
    def __new__(cls, reference: types.Reference) -> _BaseReferenceService:
        if reference.stream == types.Stream(""):
            return _MainReferenceService(reference)
        return _SubReferenceService(reference)
