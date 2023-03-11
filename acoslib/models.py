from __future__ import annotations

import datetime
import os
import pathlib
import re
import subprocess
import typing

import gi
import yaml

gi.require_version("OSTree", "1.0")

from gi.repository import OSTree, Gio

from acoslib.types import Arch, Stream, ImageFormat, Version
from acoslib.images import QcowImage, BaseImage
from acoslib.utils import cmdlib


class Repository:
    """
    Класс представления репозитория.
    Содержит необходимую информацию для работы с altcos-репозиториями.
    """

    __slots__ = (
        "_osname",
        "_root",
        "_stream_root",
        "_script_root",
        "_mkimage_root",
    )

    def __init__(self,
                 osname: str,
                 root: str | os.PathLike,
                 stream_root: str | os.PathLike,
                 script_root: str | os.PathLike,
                 mkimage_root: str | os.PathLike) -> None:
        self._osname = osname
        self._root = pathlib.Path(root)
        self._stream_root = pathlib.Path(stream_root)
        self._script_root = pathlib.Path(script_root)
        self._mkimage_root = pathlib.Path(mkimage_root)

    @property
    def osname(self) -> str:
        return self._osname

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @property
    def stream_root(self) -> pathlib.Path:
        return self._stream_root

    @property
    def script_root(self) -> pathlib.Path:
        return self._script_root

    @property
    def mkimage_root(self) -> pathlib.Path:
        return self._mkimage_root


class BareRepoExistsError(Exception):
    pass


class ImageProfileExistsError(Exception):
    pass


class Reference:
    """
    Класс представления ветки
    """
    __slots__ = (
        "_repository",
        "_arch",
        "_stream",
    )

    def __init__(self, repository: Repository, arch: Arch, stream: Stream) -> None:
        self._repository = repository
        self._arch = arch
        self._stream = stream

    @property
    def repository(self) -> Repository:
        return self._repository

    @property
    def stream(self) -> Stream:
        return self._stream

    @property
    def arch(self) -> Arch:
        return self._arch

    @property
    def ostree_ref(self) -> pathlib.Path:
        """Формирует ветку в контексте ostree-репозитория"""
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value)

    @property
    def ostree_baseref(self) -> pathlib.Path:
        """Формирует базовую ветку в контексте ostree-репозитория"""
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value)

    @property
    def ref_dir(self) -> pathlib.Path:
        """Формирует путь до ветки"""
        return pathlib.Path(str(self.ostree_ref).lower())

    @property
    def repo_dir(self) -> pathlib.Path:
        """Формирует путь до ostree-репозитория"""
        return pathlib.Path(self._repository.stream_root,
                            self._repository.osname,
                            self._arch.value,
                            self._stream.value,
                            "bare", "repo")

    @property
    def image_dir(self) -> pathlib.Path:
        """Формирует путь до образов"""
        return pathlib.Path(self.repository.stream_root, self.ref_dir, "images")

    @property
    def mkimage_dir(self) -> pathlib.Path:
        """Формирует путь до профилей"""
        return pathlib.Path(self.repository.stream_root, self.ostree_baseref, "mkimage-profiles")

    @property
    def merged_dir(self) -> pathlib.Path:
        """Формирует путь до директории, где развернута ветка"""
        return pathlib.Path(self.repository.stream_root, self.ref_dir, "roots", "merged")

    @classmethod
    def from_ostree(cls, repository: Repository, ostree_ref: str) -> Reference:
        """
        Создает экземпляр класса из ostree-записи ветки
        Например: altcos/x86_64/p10
        """
        parts = ostree_ref.split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid format of reference. Reference must be like `altcos/x86_64/p10`")

        return cls(repository, Arch(parts[1]), Stream(parts[2]))

    def ostree_repo_exists(self) -> bool:
        repo_dir = str(self.repo_dir)
        try:
            OSTree.Repo.new(Gio.File.new_for_path(repo_dir)).open(None)
        except gi.repository.GLib.GError:
            return False
        return True

    def mkprofile(self) -> Reference:
        """Создание профиля"""
        cmdlib.runcmd(
            f"{self.repository.script_root}/cmd_mkimage-profiles.sh "
            f"{self.stream.value} "
            f"{self.arch.value}"
        )
        return self

    def mkrepo(self) -> Reference:
        """Создание ostree-репозитория (необходимо наличие профиля)"""
        cmdlib.runcmd(f"sudo -E {self.repository.script_root}/cmd_rootfs2repo.sh {self.ostree_ref}")
        return self

    def checkout(self, commit: Commit) -> Reference:
        """Разворачивание коммита в merged-директорию"""
        cmdlib.runcmd(f"{self.repository.script_root}/cmd_ostree_checkout.sh {self.ostree_ref} {commit.sha256}")
        return self

    def sync(self, commit: Commit) -> Reference:
        """Синхронизация коммита"""
        cmdlib.runcmd(f"{self.repository.script_root}/cmd_sync_updates.sh "
                      f"{self.ostree_ref} {commit.version}")
        return self

    def clear_roots(self) -> Reference:
        """Удаление временных директорий"""
        cmdlib.runcmd(f"{self.repository.script_root}/cmd_clear_roots.sh {self.ostree_ref}")
        return self

    def commit(self, commit: Commit) -> Reference:
        """Коммит изменений"""
        cmdlib.runcmd(f"{self.repository.script_root}/cmd_ostree_commit.sh "
                      f"{self.ostree_ref} {commit.sha256} {commit.version}")
        return self

    def create(self) -> Reference:
        """Создание ostree-ветки"""
        if not self.mkimage_dir.exists():
            raise ImageProfileExistsError(
                f"Image profile for {self.ostree_ref} not exists. Use `mkprofile` method firstly")

        return self.mkrepo()

    def update(self) -> Reference:
        """Обновление ostree-ветки"""
        commit = Commit(self).all()[-1]

        self.clear_roots().checkout(commit)

        Apt(self).update().upgrade().update_kernel()

        commit.version.major += 1

        return self.sync(commit).commit(commit)


class SubReference(Reference):
    """
    Класс представления подветки
    """
    __slots__ = (
        "_name",
    )

    def __init__(self,
                 repository: Repository,
                 arch: Arch,
                 stream: Stream,
                 name: str) -> None:
        super().__init__(repository, arch, stream)

        self._name = name

    @property
    def ostree_ref(self) -> pathlib.Path:
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value.capitalize(),
                            self._name)

    @classmethod
    def from_ostree(cls, repository: Repository, ostree_ref: str) -> Reference:
        parts = ostree_ref.split("/")
        if len(parts) != 4:
            raise ValueError(f"Invalid format of reference. Reference must be like `altcos/x86_64/Sisyphus/k8s`")

        return cls(repository, Arch(parts[1]), Stream(parts[2].lower()), parts[3])

    @classmethod
    def from_baseref(cls, base: Reference, **extra) -> SubReference:
        return cls(base.repository, base.arch, base.stream, **extra)

    def checkout(self, commit: Commit) -> Reference:
        cmdlib.runcmd(f"{self.repository.script_root}/cmd_ostree_checkout.sh "
                      f"{self.ostree_baseref} {commit.sha256} {self.ostree_ref} all")

        return self

    def create(self) -> Reference:
        if not self.ostree_repo_exists():
            raise BareRepoExistsError(f"Bare repo does not exist for {self.ostree_ref}")

        commit = Commit(super()).all()[-1]

        self.checkout(commit)

        AltConf(self).exec(str(self.merged_dir))

        return self.sync(commit).commit(commit)


class Commit:
    __slots__ = (
        "_reference",
        "_sha256",
        "_version",
        "_date",
        "_parent_id",
    )

    _COMMIT_INFO_RE = re.compile(r"(commit .*\n(Parent:.*\n|)ContentChecksum: .*\nDate:.*\nVersion: .*\n)")

    def __init__(self, reference: Reference, **kwargs) -> None:
        self._reference = reference
        self._sha256 = kwargs.get("sha256")
        self._version = kwargs.get("version")
        self._date = kwargs.get("date")
        self._parent_id = kwargs.get("parent_id")

    @property
    def reference(self) -> Reference:
        return self._reference

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def version(self) -> Version:
        return self._version

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def parent_id(self) -> str:
        return self._parent_id

    def all(self) -> list[Commit] | None:
        cp = cmdlib.runcmd(f"ostree log {self.reference.ostree_ref} --repo {self.reference.repo_dir}")

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

            commit_list.append(Commit(self._reference,
                                      sha256=sha256,
                                      version=Version.from_str(version),
                                      date=date,
                                      parent_id=parent_id))

        return sorted(commit_list,
                      key=lambda item: item.date)

    def create(self) -> Commit:
        self.reference.checkout(self).sync(self).commit(self)
        return self


class AltConf:
    __slots__ = (
        "_subref",
        "_path",
        "_mtime",
        "_content",
        "_env",
    )

    def __init__(self, subref: SubReference) -> None:
        self._subref = subref
        self._path = pathlib.Path(self.subref.repository.stream_root,
                                  subref.ref_dir,
                                  "altconf.yml")
        self._env = {}

        with self._path.open() as file:
            self._content = yaml.safe_load(file)
            for attr in ["from", "actions"]:
                if self._content.get(attr) is None:
                    raise ValueError(f"Attribute {attr} is required")

        self._mtime = self._path.lstat().st_mtime

        if not self._subref.ostree_repo_exists():
            raise BareRepoExistsError(f"Bare repo does not exist for {self._subref.ostree_ref}")

    @property
    def subref(self) -> SubReference:
        return self._subref

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @property
    def mtime(self) -> float:
        return self._mtime

    def exec(self, merged_dir: str) -> None:
        self._env["MERGED_DIR"] = merged_dir

        actions = self._content.get("actions")

        for sub_act in actions:
            for k, v in sub_act.items():
                if v is None:
                    continue

                match k:
                    case "rpms":
                        self._rpm_act(v)
                    case "env":
                        self._env_act(v, merged_dir)
                    case "podman":
                        self._podman_act(v, merged_dir)
                    case "butane":
                        self._butane_act(v, merged_dir)
                    case "run":
                        self._run_act(v, merged_dir)

    def _rpm_act(self, value: list[str]) -> None:
        script_root = self._subref.repository.script_root

        cmdlib.runcmd(
            f"stdbuf -oL {script_root}/cmd_apt-get_update.sh {self._subref.ostree_ref}")

        pkg_names = " ".join(value)

        cmdlib.runcmd(
            f"stdbuf -oL {script_root}/cmd_apt-get_install.sh {self._subref.ostree_ref} {pkg_names}")

    def _env_act(self, value: dict, merged_dir: str) -> None:
        for k, v in value.items():
            cmd = self._make_export_env_cmd()
            if isinstance(v, dict):
                if env_cmd := v.get("cmd"):
                    cmd += f"sudo chroot {merged_dir} sh -c \"{env_cmd}\""
            else:
                cmd += f"{k}=\"{v}\";echo ${k}"

            self._env[k] = cmdlib.runcmd(cmd).stdout.decode().replace("\n", " ")

    def _podman_act(self, value: dict, merged_dir: str) -> None:
        images = value.get("images")
        env_list_images = value.get("envListImages")

        if not images and env_list_images:
            return

        if images:
            images = " ".join(images)

            if env_list_images:
                for env_name in env_list_images.split(','):
                    images += f" {self._env[env_name]}"

            cmd = f"{self._subref.repository.script_root}/cmd_skopeo_copy.sh {merged_dir} {images}"

            cmdlib.runcmd(
                f"{self._make_export_env_cmd()}{cmd}"
            )

    def _butane_act(self, value: dict, merged_dir: str) -> None:
        script_root = self._subref.repository.script_root
        butane_yml = yaml.safe_dump(value)

        abs_ref_dir = self._subref.ref_dir.absolute()
        cmd = f"echo \"{butane_yml}\" | {script_root}/cmd_ignition.sh {abs_ref_dir} {merged_dir}"
        cmdlib.runcmd(
            f"{self._make_export_env_cmd()}{cmd}",
        )

    def _run_act(self, value: typing.Any, merged_dir: str) -> None:
        cmd = f"sudo chroot {merged_dir} bash -c \"{''.join(value)}\""
        cmdlib.runcmd(
            f"{self._make_export_env_cmd()}{cmd}"
        )

    def _make_export_env_cmd(self) -> str:
        """
        Формирует команду для экспорта переменных окружения из self._env
        :return:
        """
        cmd = [f"export {k}=\"{v}\"" for k, v in self._env.items()]
        return ";".join(cmd).strip() + ";"


class Image:
    _FACTORY_LIST = {
        ImageFormat.QCOW: QcowImage,
    }

    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: Reference) -> None:
        self._reference = reference

    def create(self, img_format: ImageFormat, commit_id: str) -> BaseImage:
        return self._FACTORY_LIST.get(img_format).create(self._reference, commit_id)

    def all(self, img_format: ImageFormat) -> list[BaseImage]:
        return self._FACTORY_LIST.get(img_format).all(self._reference)


class Apt:
    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: Reference) -> None:
        self._reference = reference

    def install(self, *pkgs) -> subprocess.CompletedProcess:
        return cmdlib.runcmd(f"stdbuf -oL {self._reference.repository.script_root}/cmd_apt-get_install.sh "
                             f"{self._reference.ostree_ref} {' '.join(*pkgs)}")

    def update(self) -> Apt:
        cmdlib.runcmd(f"stdbuf -oL {self._reference.repository.script_root}/cmd_apt-get_update.sh "
                      f"{self._reference.ostree_ref}")
        return self

    def upgrade(self) -> Apt:
        cmdlib.runcmd(f"{self._reference.repository.script_root}/cmd_apt-get_dist-upgrade.sh "
                      f"{self._reference.ostree_ref}")

        return self

    def update_kernel(self) -> Apt:
        cmdlib.runcmd(f"{self._reference.repository.script_root}/cmd_update_kernel.sh {self._reference.ostree_ref}")

        return self
