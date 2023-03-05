import json
import os.path

from acoslib.utils import repo


class RefConf:
    """
    Класс для обработки ref_conf.json
    """
    __slots__ = (
        "_ref",
        "_version",
        "_added_pkgs",
        "_ref_repo_dir",
        "_ref_dir",
        "_vars_dir",
        "_version_dir",
        "_ref_conf_file",
        "_data",
    )

    def __init__(self, ref: str, version: str, added_pkgs: list[str] = None):
        self._ref = ref
        self._version = version
        self._added_pkgs = added_pkgs
        self._ref_repo_dir = repo.to_baseref(self._ref)
        self._ref_dir = os.path.join(repo.MetaInfo.STREAMS_ROOT, self._ref_repo_dir)
        self._vars_dir = os.path.join(self._ref_dir, "vars")
        self._version_dir = os.path.join(self._vars_dir, repo.version_var_subdir(self._version))
        self._ref_conf_file = os.path.join(self._version_dir, "ref_conf.json")

        if os.path.exists(self._ref_conf_file):
            with open(self._ref_conf_file) as file:
                self._data = json.load(file)
        else:
            self._data = {
                "ref": self._ref,
                "version": self._version,
            }

        if added_pkgs:
            self._data["added_pkgs"] = self._added_pkgs

    def save(self):
        old_conf = f"{self._ref_conf_file}.old"
        if os.path.exists(old_conf):
            os.unlink(old_conf)

        if os.path.exists(self._ref_conf_file):
            os.rename(self._ref_conf_file, old_conf)

        with open(self._ref_conf_file, "w") as file:
            json.dump(self._data, file)

    def get_rpm_short_name(self, rpm_fullname) -> str:
        return "-".join(rpm_fullname.split('-')[:-2])

    def add_rpm_list(self, rpm_list: list[str]):
        rpm_list.sort()
        self._data["rpm_list_full_names"] = rpm_list
        self.set_rpm_list_short_names(rpm_list)

    def set_rpm_list_short_names(self, rpm_list: list[str] = None):
        if not rpm_list:
            rpm_list = self._data["rpm_list_full_names"]

        self._data["rpm_list_short_names"] = []
        for fullname in rpm_list:
            self._data["rpm_list_short_names"].append(self.get_rpm_short_name(fullname))

    @property
    def ref(self) -> str:
        return self._ref

    @property
    def version(self) -> str:
        return self._version

    @property
    def added_pkgs(self) -> list[str]:
        return self._added_pkgs
