from __future__ import annotations

import re
from datetime import datetime

from acoslib import services
from acoslib import types
from acoslib.utils import cmdlib


class CommitService(services.BaseService):

    _COMMIT_INFO_RE = re.compile(r"(commit .*\n(Parent:.*\n|)ContentChecksum: .*\nDate:.*\nVersion: .*\n)")

    def list(self) -> list[types.OSTreeCommit] | None:
        cp = cmdlib.runcmd(f"ostree log {self.reference} --repo {self.reference.repodir}")
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

            commit_list.append(types.OSTreeCommit(sha256=sha256,
                                                  version=version,
                                                  date=date,
                                                  parent_id=parent_id))

        return sorted(commit_list,
                      key=lambda item: item.date)

    def checkout(self, commit: types.OSTreeCommit) -> CommitService:
        if self.reference.stream != types.Stream(""):
            cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_checkout.sh "
                          f"{self.reference.baseref} {commit.sha256} {self.reference} all")
        else:
            cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_checkout.sh "
                          f"{self.reference} {commit.sha256}")
        return self

    def sync(self, commit: types.OSTreeCommit) -> CommitService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_sync_updates.sh "
                      f"{self.reference} {commit.sha256} {str(commit.version)}")
        return self

    def commit(self, commit: types.OSTreeCommit) -> CommitService:
        cmdlib.runcmd(f"{self.reference.repository.script_root}/cmd_ostree_commit.sh "
                      f"{self.reference} {commit.sha256} {str(commit.version)}")
        return self

