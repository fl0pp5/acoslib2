from __future__ import annotations

import dataclasses
import datetime
import pathlib
import re
import typing

import yaml

from acoslib.types import Arch, Stream, ImageFormat, Version, Branch, AltcosRepoPaths, OSName, Commit, PkgName
from acoslib.images import QcowImage, BaseImage
from acoslib.utils import cmdlib


class BareRepoExistsError(Exception):
    pass


class ImageProfileExistsError(Exception):
    pass


@dataclasses.dataclass
class Reference:
    altcos_paths: AltcosRepoPaths
    osname: OSName
    arch: Arch
    branch: Branch
    stream: Stream = Stream("")

    _COMMIT_INFO_RE = re.compile(r"(commit .*\n(Parent:.*\n|)ContentChecksum: .*\nDate:.*\nVersion: .*\n)")

    def __str__(self) -> str:
        return str(pathlib.Path(self.osname.value,
                                self.arch.value,
                                self.branch.value.capitalize() if not self.is_base() else self.branch.value,
                                self.stream))

    @property
    def baseref(self) -> Reference:
        return Reference(self.altcos_paths, self.osname, self.arch, self.branch, Stream(""))

    @property
    def basedir(self) -> pathlib.Path:
        """
        Forms the path to the base branch directory. e.g. `builds/streams/altcos/x86_64/p10`
        """
        return pathlib.Path(self.altcos_paths.stream_root,
                            self.osname.value,
                            self.arch.value,
                            self.branch.value,
                            self.stream)

    @property
    def location(self) -> pathlib.Path:
        """
        Forms the path to current branch.
        """
        return self.basedir

    @property
    def repodir(self) -> pathlib.Path:
        """
        Forms the path to the ostree repository
        """
        return self.basedir.joinpath("bare", "repo")

    @property
    def imagedir(self) -> pathlib.Path:
        """
        Forms the path to the images directory
        """
        return self.location.joinpath("images")

    @property
    def mkpdir(self) -> pathlib.Path:
        """
        Forms the path to the profiles directory
        """
        return self.basedir.joinpath("mkimage-profiles")

    @property
    def mergedir(self) -> pathlib.Path:
        """
        Forms the path to the merged directory
        """
        return self.location.joinpath("roots", "merged")

    @property
    def altconf(self) -> pathlib.Path:
        """
        Forms the path to the config file
        """
        return self.location.joinpath("altconf.yml")

    @property
    def rootdir(self) -> pathlib.Path:
        """
        Forms the path to the custom root directory
        """
        return self.location.joinpath("root")

    def is_base(self) -> bool:
        return self.stream == Stream("")

    def clear_roots(self) -> Reference:
        cmdlib.runcmd(f"{self.altcos_paths.script_root}/cmd_clear_roots.sh {self}")
        return self

    def checkout(self, commit: Commit) -> Reference:
        if self.is_base():
            cmdlib.runcmd(f"{self.altcos_paths.script_root}/cmd_ostree_checkout.sh {self} {commit.sha256}")
        else:
            cmdlib.runcmd(f"{self.altcos_paths.script_root}/cmd_ostree_checkout.sh "
                          f"{self.baseref} {commit.sha256} {self} all")
        return self

    def sync(self, commit: Commit) -> Reference:
        cmdlib.runcmd(f"{self.altcos_paths.script_root}/cmd_sync_updates.sh {self} {commit.sha256} {commit.version}")
        return self

    def mkrepo(self) -> Reference:
        if not self.mkpdir.exists():
            raise ImageProfileExistsError(f"Image profile for {self} not exists.")

        cmdlib.runcmd(f"sudo -E {self.altcos_paths.script_root}/cmd_rootfs2repo.sh {self}")
        return self

    def mkprofile(self, recreate: bool = False) -> Reference:
        if self.mkpdir.exists() and not recreate:
            raise ImageProfileExistsError(f"Image profile for {self} exists. If you want to recreate, set the flag.")

        cmdlib.runcmd(
            f"{self.altcos_paths.script_root}/cmd_mkimage-profiles.sh "
            f"{self.branch.value} "
            f"{self.arch.value}"
        )
        return self

    def log(self) -> list[Commit] | None:
        cp = cmdlib.runcmd(f"ostree log {self} --repo {self.repodir}")

        info = self._COMMIT_INFO_RE.findall(cp.stdout.decode())

        if not info:
            return None

        commit_list = []

        for part in info:
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
                        date = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
                    case "parent:":
                        parent_id = value

            commit_list.append(Commit(sha256=sha256,
                                      version=Version.from_str(version),
                                      date=date,
                                      parent_id=parent_id))

        return sorted(commit_list,
                      key=lambda item: item.date)

    def commit(self, base: Commit) -> Reference:
        cmdlib.runcmd(f"{self.altcos_paths.script_root}/cmd_ostree_commit.sh "
                      f"{self} {base.sha256} {base.version}")
        return self

    def create(self) -> Reference:
        return self._create_main() if self.is_base() else self._create_sub()

    def _create_main(self) -> Reference:
        return self.mkrepo()

    def _create_sub(self) -> Reference:
        if not self.repodir.exists():
            raise BareRepoExistsError(f"Bare repo does not exist for {self}")

        commit = self.baseref.log()[-1]
        self.checkout(commit)
        AltConf(self).exec()

        return self.sync(commit).commit(commit)


class AltConf:
    __slots__ = (
        "_reference",
        "_env",
    )

    def __init__(self, reference: Reference) -> None:
        self._reference = reference
        self._env = {}

    @property
    def reference(self) -> Reference:
        return self._reference

    @property
    def _export_env_cmd(self) -> str:
        cmd = [f"export {k}=\"{v}\"" for k, v in self._env.items()]
        return ";".join(cmd).strip() + ";"

    def exec(self) -> None:
        self._env["MERGED_DIR"] = self.reference.mergedir

        with open(self.reference.altconf) as file:
            actions = yaml.safe_load(file).get("actions")

        allowed_actions = {
            "rpms": self._rpm_act,
            "env": self._env_act,
            "podman": self._podman_act,
            "butane": self._butane_act,
            "run": self._run_act,
        }

        for act in actions:
            for key, value in act.items():
                if value is None:
                    continue

                allowed_actions.get(key)(value)

    def _rpm_act(self, value: list[PkgName]) -> None:
        Apt(self.reference).update().install(*value)

    def _env_act(self, value: dict) -> None:
        for k, v in value.items():
            cmd = self._export_env_cmd
            if isinstance(v, dict):
                if env_cmd := v.get("cmd"):
                    cmd += f"sudo chroot {self.reference.mergedir} sh -c \"{env_cmd}\""
            else:
                cmd += f"{k}=\"{v}\";echo ${k}"

            self._env[k] = cmdlib.runcmd(cmd).stdout.decode().replace("\n", " ")

    def _podman_act(self, value: dict) -> None:
        images = value.get("images")
        env_list_images = value.get("envListImages")

        if not images and env_list_images:
            return

        if images:
            images = " ".join(images)

            if env_list_images:
                for env_name in env_list_images.split(','):
                    images += f" {self._env[env_name]}"

            cmd = f"{self.reference.repository.script_root}/cmd_skopeo_copy.sh {self.reference.mergedir} {images}"

            cmdlib.runcmd(f"{self._export_env_cmd}{cmd}")

    def _butane_act(self, value: dict) -> None:
        script_root = self.reference.repository.script_root
        butane_yml = yaml.safe_dump(value)

        abs_ref_dir = self.reference.refdir.absolute()
        cmd = f"echo \"{butane_yml}\" | {script_root}/cmd_ignition.sh {abs_ref_dir} {self.reference.mergedir}"
        cmdlib.runcmd(f"{self._export_env_cmd}{cmd}")

    def _run_act(self, value: typing.Any) -> None:
        cmd = f"sudo chroot {self.reference.mergedir} bash -c \"{''.join(value)}\""
        cmdlib.runcmd(f"{self._export_env_cmd}{cmd}")


class Image:
    _FACTORY_LIST = {
        ImageFormat.QCOW: QcowImage,
    }

    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: Reference) -> None:
        self._reference = reference

    def create(self, img_format: ImageFormat, commit_id: str) -> Image:
        self._FACTORY_LIST.get(img_format).create(self._reference, commit_id)
        return self

    def all(self, img_format: ImageFormat) -> list[BaseImage]:
        return self._FACTORY_LIST.get(img_format).all(self._reference)


class Apt:
    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: Reference) -> None:
        self._reference = reference

    @property
    def reference(self) -> Reference:
        return self._reference

    def install(self, *pkgs: PkgName) -> Apt:
        cmdlib.runcmd(f"stdbuf -oL {self.reference.altcos_paths.script_root}/cmd_apt-get_install.sh "
                      f"{self.reference} {' '.join(pkgs)}")
        return self

    def update(self) -> Apt:
        cmdlib.runcmd(f"stdbuf -oL {self.reference.altcos_paths.script_root}/cmd_apt-get_update.sh "
                      f"{self.reference}")
        return self

    def upgrade(self) -> Apt:
        cmdlib.runcmd(f"{self.reference.altcos_paths.script_root}/cmd_apt-get_dist-upgrade.sh "
                      f"{self.reference}")
        return self

    def update_kernel(self) -> Apt:
        cmdlib.runcmd(f"{self.reference.altcos_paths.script_root}/cmd_update_kernel.sh "
                      f"{self.reference}")
        return self

    def list(self) -> list[PkgName]:
        output = cmdlib.runcmd(f"{self.reference.altcos_paths.script_root}/cmd_rpm_list.sh "
                               f"{self.reference}").stdout.decode()

        return [PkgName(pkg) for pkg in output.split("\n")][:-1]
