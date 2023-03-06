from __future__ import annotations

import datetime
import pathlib
import re
import typing

import gi
import yaml

gi.require_version("OSTree", "1.0")

from gi.repository import OSTree, Gio

from acoslib.types import Arch, Stream
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

    def __init__(self, osname: str, root: str, stream_root: str, script_root: str, mkimage_root: str):
        self._osname = osname
        self._root = root
        self._stream_root = stream_root
        self._script_root = script_root
        self._mkimage_root = mkimage_root

        for attr in self.__slots__:
            if getattr(self, attr) is None:
                raise ValueError(f"Attribute {attr} is required")

    @property
    def osname(self) -> str:
        return self._osname

    @property
    def root(self) -> str:
        return self._root

    @property
    def stream_root(self) -> str:
        return self._stream_root

    @property
    def script_root(self) -> str:
        return self._script_root

    @property
    def mkimage_root(self) -> str:
        return self._mkimage_root


class BareRepoExistenceError(Exception):
    pass


class Reference:
    __slots__ = (
        "_repository",
        "_arch",
        "_stream",
    )

    def __init__(self, repository: Repository, arch: Arch, stream: Stream):
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
        """Формирует (под)ветку"""
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value)

    @property
    def ostree_baseref(self) -> pathlib.Path:
        """Формирует базовую ветку"""
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value)

    @property
    def ostree_ref_dir(self) -> pathlib.Path:
        return pathlib.Path(str(self.ostree_ref).lower())

    @property
    def repo_path(self) -> pathlib.Path:
        return pathlib.Path(self._repository.stream_root,
                            self._repository.osname,
                            self._arch.value,
                            self._stream.value,
                            "bare", "repo")

    @property
    def version(self, commit_id: str = None):
        if not commit_id:
            date, major, minor = datetime.datetime.now().strftime("%Y%m%d"), 0, 0
        else:
            vars_path = pathlib.Path(self.repository.stream_root, self.ostree_ref, "vars")
            commit_link = pathlib.Path(vars_path, commit_id)

            link_target = commit_link.readlink()

            date, major, minor = link_target[:3]

        path = str(self.ostree_ref).lower().split('/')
        stream = '_'.join(path[2:])

        return f"{stream}.{date}.{major}.{minor}"

    @classmethod
    def from_ostree(cls, repository: Repository, ostree_ref: str, **extra) -> Reference:
        parts = ostree_ref.split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid format of reference. Reference must be like `altcos/x86_64/p10`")

        return cls(repository, Arch(parts[1]), Stream(parts[2]))

    def ostree_repo_exists(self) -> bool:
        repo_path = str(self.repo_path)
        try:
            OSTree.Repo.new(Gio.File.new_for_path(repo_path)).open(None)
        except gi.repository.GLib.GError:
            return False
        return True

    def create(self) -> None:
        cmdlib.runcmd(f"sudo -E {self.repository.script_root}/cmd_rootfs2repo.sh {self.ostree_ref}")


class SubReference(Reference):
    __slots__ = (
        "_name",
        "_altconf",
        "_root_dir"
    )

    def __init__(self, repository: Repository, arch: Arch, stream: Stream,
                 name: str, altconf: str = None, root_dir: str = None):
        super().__init__(repository, arch, stream)

        self._name = name
        self._altconf = pathlib.Path(altconf)
        self._root_dir = pathlib.Path(root_dir)

        if self._altconf and not self._altconf.exists():
            raise FileExistsError(f"altcos config file {self._altconf} not exists")

        if self._root_dir and not self._root_dir.exists():
            raise FileExistsError(f"root directory {self._root_dir} not exists")

    @property
    def ostree_ref(self) -> pathlib.Path:
        return pathlib.Path(self._repository.osname,
                            self._arch.value,
                            self._stream.value.capitalize(),
                            self._name)

    @property
    def altconf(self) -> pathlib.Path:
        return self._altconf

    @property
    def root_dir(self) -> pathlib.Path:
        return self._root_dir

    @classmethod
    def from_ostree(cls, repository: Repository, ostree_ref: str, **extra) -> Reference:
        parts = ostree_ref.split("/")
        if len(parts) != 4:
            raise ValueError(f"Invalid format of reference. Reference must be like `altcos/x86_64/Sisyphus/k8s`")

        return cls(repository, Arch(parts[1]), Stream(parts[2].lower()), parts[3])

    @classmethod
    def from_baseref(cls, base: Reference, **extra) -> SubReference:
        return cls(base.repository, base.arch, base.stream, **extra)

    def create(self) -> None:
        script_root = self.repository.script_root
        stream_root = self.repository.stream_root

        if self._root_dir or self._altconf:
            cmdlib.runcmd(
                f"sudo -E {script_root}/cmd_create_subref_files.sh "
                f"{self.ostree_ref_dir} "
                f"{self.altconf} "
                f"{self.root_dir}")

        merged_dir = pathlib.Path(stream_root, self.ostree_ref_dir, "roots", "merged")

        last_commit = Commit(super()).all()[-1]
        last_commit_id = last_commit.sha256

        cmdlib.runcmd(
            f"{script_root}/cmd_ostree_checkout.sh {self.ostree_baseref} {last_commit_id} {self.ostree_ref} all")

        AltConf(self).exec(str(merged_dir))

        cmdlib.runcmd(
            f"{script_root}/cmd_sync_updates.sh {self.ostree_ref} {last_commit_id} {self.version}")

        cmdlib.runcmd(
            f"{script_root}/cmd_ostree_commit.sh {self.ostree_ref} {last_commit_id} {self.version}")


class Commit:
    __slots__ = (
        "_reference",
        "_sha256",
        "_version",
        "_date",
        "_parent_id",
    )

    _COMMIT_INFO_RE = re.compile(r"(commit .*\n(Parent:.*\n|)ContentChecksum: .*\nDate:.*\nVersion: .*\n)")

    def __init__(self, reference: Reference, **kwargs):
        self._reference: Reference = reference
        self._sha256: str = kwargs.get("sha256")
        self._version: str = kwargs.get("version")
        self._date: datetime.datetime = kwargs.get("date")
        self._parent_id: str = kwargs.get("parent_id")

    @property
    def reference(self) -> Reference:
        return self._reference

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def version(self) -> str:
        return self._version

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def parent_id(self) -> str:
        return self._parent_id

    def all(self) -> list[Commit] | None:
        cp = cmdlib.runcmd(
            f"ostree log {self._reference.ostree_ref} --repo {self._reference.repo_path}"
        )

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
                                      version=version,
                                      date=date,
                                      parent_id=parent_id))

        return sorted(commit_list,
                      key=lambda item: item.date)

    def create(self, commit_id: str, version: str) -> None:
        ostree_baseref = self.reference.ostree_baseref
        ostree_ref = self.reference.ostree_ref
        scripts_root = self._reference.repository.script_root

        if ostree_baseref != ostree_ref:
            cmdlib.runcmd(
                cmd=f"{scripts_root}/cmd_ostree_checkout.sh {ostree_baseref} {commit_id} {self.reference} all"
            )
        else:
            cmdlib.runcmd(
                cmd=f"{scripts_root}/cmd_ostree_checkout.sh {ostree_baseref} {commit_id}"
            )

        cmdlib.runcmd(
            cmd=f"{scripts_root}/cmd_sync_updates.sh {ostree_ref} {commit_id} {version}"
        )

        cmdlib.runcmd(
            cmd=f"{scripts_root}/cmd_ostree_commit.sh {ostree_ref} {commit_id} {version}"
        )


class AltConf:
    __slots__ = (
        "_subref",
        "_path",
        "_mtime",
        "_content",
        "_env",
    )

    def __init__(self, subref: SubReference):
        self._subref = subref
        self._path = pathlib.Path(self.subref.repository.stream_root,
                                  subref.ostree_ref_dir,
                                  "altcos.yml")
        self._env = {}

        with self._path.open() as file:
            self._content = yaml.safe_load(file)
            for attr in ["from", "actions"]:
                if self._content.get(attr) is None:
                    raise ValueError(f"Attribute {attr} is required")

        self._mtime = self._path.lstat().st_mtime

        if not self._subref.ostree_repo_exists():
            raise BareRepoExistenceError(f"Bare repo does not exist for {self._subref.ostree_ref}")

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
                        pass
                        self._rpm_act(v)
                    case "env":
                        self._env_act(v, merged_dir)
                        pass
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

        abs_ref_dir = self._subref.ostree_ref_dir.absolute()
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
