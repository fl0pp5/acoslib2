from __future__ import annotations

from acoslib import services, types
from acoslib.utils import cmdlib


class ReferenceService(services.RepositoryService):
    def __init__(self, reference: types.Reference) -> None:
        super().__init__(reference)

    def mkprofile(self) -> ReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_mkimage-profiles.sh "
                      f"{self.reference.branch.value} "
                      f"{self.reference.arch.value}")

        return self

    def mkrepo(self) -> ReferenceService:
        cmdlib.runcmd(f"sudo -E {self.reference.repository.script_root}/cmd_rootfs2repo.sh "
                      f"{self.ostree.ref}")

        return self


