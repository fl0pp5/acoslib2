from __future__ import annotations

import datetime
import enum
import logging
import os.path
import pathlib
import subprocess

import gi

from acoslib.utils import cmdlib

gi.require_version("OSTree", "1.0")

from gi.repository import OSTree, Gio


class RefExistsError(Exception):
    pass


class RepoNotExists(Exception):
    pass


class ALTCOSFileNotExistsError(Exception):
    pass


class ALTCOSFileAttrNotExistsError(Exception):
    pass


class BareRepoNotExistsError(Exception):
    pass


class MetaInfo:
    ALTCOS_ROOT = os.getenv("ALTCOS_ROOT", ".")
    BUILDS_ROOT = os.getenv("BUILDS_ROOT", os.path.join(ALTCOS_ROOT, "builds"))
    SCRIPTS_ROOT = os.getenv("SCRIPTS_ROOT", os.path.join(ALTCOS_ROOT, "scripts"))
    STREAMS_ROOT = os.getenv("STREAMS_ROOT", os.path.join(BUILDS_ROOT, "streams"))


class Stream(enum.Enum):
    Sisyphus = "sisyphus"
    P10 = "p10"


class Arch(enum.Enum):
    X86_64 = "x86_64"


def make_ref(arch: Arch, stream: Stream, substream: str = None) -> str:
    """
    Формирует ветку вида
    Пример:
        altcos/$arch/$stream/$substream => altcos/x86_64/Sisyphus/k8s
    :param arch:
    :param stream:
    :param substream:
    :return:
    """
    if substream:
        return os.path.join("altcos", arch.value, stream.value.capitalize(), substream)
    return os.path.join("altcos", arch.value, stream.value)


def to_baseref(ref: str) -> str:
    """
    Формирует родительскую ветку
    Пример:
        altcos/x86_64/sisyphus => altcos/x86_64/sisyphus
        altcos/x86_64/Sisyphus/k8s => altcos/x86_64/sisyphus
    :param ref:
    :return:
    """
    path = ref.split('/')[:3]
    return '/'.join(path).lower()


def get_repo_path(ref: str) -> str:
    """
    Формирует путь до папки репозитория исходя из ветки
    :param ref:
    :return:
    """
    return os.path.join(MetaInfo.STREAMS_ROOT, to_baseref(ref), "bare", "repo")


def repo_exists(ref: str) -> bool:
    try:
        OSTree.Repo.new(Gio.File.new_for_path(get_repo_path(ref))).open(None)
    except gi.repository.GLib.GError:
        return False

    return True


def ref_to_dir(ref: str) -> str:
    return ref.lower()


def ref_version(ref: str, commit_id=None) -> str:
    """
    Формирует версию исходя из ветки
    Пример:
       altcos/x86_64/Sisyphus/apache -> sisyphus_apache.$date.$major.$minor 
    :param ref:
    :param commit_id:
    :return:
    """
    if not commit_id:
        date, major, minor = datetime.datetime.now().strftime("%Y%m%d"), 0, 0
    else:
        vars_path = os.path.join(MetaInfo.STREAMS_ROOT, ref, "vars")
        commit_link = os.path.join(vars_path, commit_id)

        link_target = os.readlink(commit_link)

        path = link_target.split('/')
        date, major, minor = path[:3]

    path = ref.lower().split('/')
    stream = '_'.join(path[2:])

    return f"{stream}.{date}.{major}.{minor}"


def altcos_file_from_ref(ref: str) -> str:
    """
    Формирует путь к файлу altcos.yml, находящегося внутри подпотока
    Пример:
        altcos/x86_64/p10/k8s => altcos/x86_64/p10/k8s/altcos.yml
    :param ref:
    :return:
    """
    return os.path.join(MetaInfo.STREAMS_ROOT, ref, "altcos.yml")


def ref_images_dir(ref: str) -> str:
    """
    Формирует путь к директории images, в которой лежат образы
    Пример:
        altcos/x86_64/p10/k8s => altcos/x86_64/p10/k8s/images
    :param ref: ветка вида
    :return:
    """
    return os.path.join(MetaInfo.STREAMS_ROOT, ref_to_dir(ref), "images")


def version_var_subdir(version: str) -> str:
    """
    Формирует путь исходя из версии
    Пример:
        sisyphus.20210914.0.0 => 20210914/0/0
        sisyphus_apache.20210914.0.0 => apache/20210914/0/0
    :param version: 
    :return: 
    """
    parts = version.lower().split(".")
    date, major, minor = parts[1:4]

    subref = ""
    ref_parts = parts[0].split("_")
    if len(ref_parts) > 1:
        subref = ref_parts[1]

    return os.path.join(subref, date, major, minor)


def is_updated(apt_out: list[str]) -> bool:
    raise NotImplementedError


def get_rpm_list(ref: str, version: str) -> list[str] | None:
    vars_dir = pathlib.Path(MetaInfo.STREAMS_ROOT, ref, "vars")
    version_dir = pathlib.Path(vars_dir, version_var_subdir(version))

    try:
        output = cmdlib.runcmd(cmd=f"rpm -qa --dbpath={version_dir}/var/lib/rpm").stdout.decode()
    except subprocess.CalledProcessError:
        logging.info(f"{version_dir}/var/lib/rpm not exists at {ref}")
        return None

    return [rpm for rpm in output.split() if rpm.strip()]

