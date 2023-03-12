import pprint
import typing

import yaml

from acoslib import services, types
from acoslib.utils import cmdlib


class AltConfService(services.BaseService):
    __slots__ = (
        "_env",
    )

    def __init__(self, reference: types.Reference) -> None:
        super().__init__(reference)
        self._env = {}

    @property
    def _export_env_cmd(self) -> str:
        cmd = [f"export {k}=\"{v}\"" for k, v in self._env.items()]
        return ";".join(cmd).strip() + ";"

    def exec(self, altconf: types.AltConf) -> None:
        self._env["MERGED_DIR"] = self.reference.mergedir

        with open(altconf) as file:
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

    def _rpm_act(self, value: list[types.RpmPackage]) -> None:
        services.AptService(self.reference).update().install(*value)

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
