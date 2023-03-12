from __future__ import annotations

from acoslib import services
from acoslib.utils import cmdlib


class MkProfileService(services.AltcosService):
    def mkprofile(self) -> MkProfileService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_mkimage-profiles.sh "
                      f"{self.reference.branch.value} "
                      f"{self.reference.arch.value}")
        return self
