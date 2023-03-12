from __future__ import annotations

import pprint

from acoslib import services, types
from acoslib.utils import cmdlib


class AptService(services.AltcosService):
    def install(self, *pkgs: types.RpmPackage) -> AptService:
        cmdlib.runcmd(f"stdbuf -oL {self.reference.repository.script_root}/cmd_apt-get_install.sh "
                      f"{self.reference} {' '.join(pkgs)}")
        return self

    def update(self) -> AptService:
        cmdlib.runcmd(f"stdbuf -oL {self.reference.repository.script_root}/cmd_apt-get_update.sh "
                      f"{self.reference}")
        return self

    def upgrade(self) -> AptService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_apt-get_dist-upgrade.sh "
                      f"{self.reference}")
        return self

    def update_kernel(self) -> AptService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_update_kernel.sh "
                      f"{self.reference}")
        return self

    def list(self) -> list[types.RpmPackage]:
        output = cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_rpm_list.sh "
                               f"{self.reference}").stdout.decode()

        return [types.RpmPackage(pkg) for pkg in output.split("\n")][:-1]
