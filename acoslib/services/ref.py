from __future__ import annotations

import re
from datetime import datetime

from acoslib import services, types
from acoslib.utils import cmdlib
from abc import ABC, abstractmethod


class _BaseReferenceService(services.AltcosService, ABC):
    _COMMIT_INFO_RE = re.compile(r"(commit .*\n(Parent:.*\n|)ContentChecksum: .*\nDate:.*\nVersion: .*\n)")

    def clear_roots(self) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_clear_roots.sh "
                      f"{self.reference}")
        return self

    def update(self) -> _BaseReferenceService:
        last_commit = self.log()[-1]

        self.clear_roots().checkout(last_commit)

        services.AptService(self.reference).update().upgrade().update_kernel()

        last_commit.version.major += 1

        return self.sync(last_commit).commit(last_commit)

    def log(self, reference: types.Reference = None) -> list[types.Commit] | None:
        reference = reference or self.reference

        cp = cmdlib.runcmd(f"ostree log {reference} --repo {reference.repodir}")
        content = self._COMMIT_INFO_RE.findall(cp.stdout.decode())

        if not content:
            return None

        commit_list = []

        for part in content:
            [sha256, version, date, parent_id] = [None] * 4

            for field in part[0].split('\n'):
                if not field:
                    continue

                raw = field.split()
                name, value = raw[0], ' '.join(raw[1:])

                match name.lower():
                    case "commit":
                        sha256 = value
                    case "version:":
                        version = value
                    case "date:":
                        date = datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
                    case "parent:":
                        parent_id = value

            commit_list.append(types.Commit(sha256=sha256,
                                            version=version,
                                            date=date,
                                            parent_id=parent_id))

        return sorted(commit_list,
                      key=lambda item: item.date)

    def sync(self, commit: types.Commit) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_sync_updates.sh "
                      f"{self.reference} {commit.sha256} {str(commit.version)}")
        return self

    def commit(self, commit: types.Commit) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_commit.sh "
                      f"{self.reference} {commit.sha256} {str(commit.version)}")
        return self

    @abstractmethod
    def mkref(self, **extra) -> _BaseReferenceService:
        pass

    @abstractmethod
    def checkout(self, commit: types.Commit) -> _BaseReferenceService:
        pass


class _MainReferenceService(_BaseReferenceService):
    def mkref(self) -> _BaseReferenceService:
        return self.mkrepo()

    def checkout(self, commit: types.Commit) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_checkout.sh "
                      f"{self.reference} {commit.sha256}")
        return self

    def mkrepo(self) -> _MainReferenceService:
        cmdlib.runcmd(f"sudo -E {self.reference.repository.script_root}/cmd_rootfs2repo.sh "
                      f"{self.reference}")
        return self


class _SubReferenceService(_BaseReferenceService):
    def mkref(self, altconf: types.AltConf) -> _BaseReferenceService:
        last_parent_commit = self.log(self.reference.baseref)[-1]

        self.checkout(last_parent_commit)

        services.AltConfService(self.reference).exec(altconf)

        return self.sync(last_parent_commit).commit(last_parent_commit)

    def checkout(self, commit: types.Commit) -> _BaseReferenceService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_checkout.sh "
                      f"{self.reference.baseref} {commit.sha256} {self.reference} all")
        return self


class ReferenceService(services.AltcosService):
    _FACTORY_LIST = {
        types.Stream(""): _MainReferenceService,
    }

    def __new__(cls, reference: types.Reference) -> _BaseReferenceService:
        return cls._FACTORY_LIST.get(reference.stream, _SubReferenceService)(reference)
