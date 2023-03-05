from acoslib.utils import cmdlib, repo


def mkimage_profiles(stream: repo.Stream, arch: repo.Arch):
    cmdlib.runcmd(cmd=f"{repo.MetaInfo.SCRIPTS_ROOT}/cmd_mkimage-profiles.sh {stream.value} {arch.value}")