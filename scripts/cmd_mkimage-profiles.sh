#!/usr/bin/env bash


if [ "$UID" = 0 ]
then
    echo "Can't run as superuser" && exit 1
fi

if [[ "$1" != "sisyphus" && "$1" != "p10" ]]
then
    echo "Format: $0 sisyphus|p10" && exit 1
fi

if [[ "$2" != "x86_64" ]]
then
    echo "Format: $0 sisyphus|p10 x86_64" && exit 1
fi

branch=$1
arch=$2

if [ "$branch" = "sisyphus" ]
then
    pkg_repo_branch="Sisyphus"
    ns="alt"
else
    pkg_repo_branch="$branch/branch"
    ns=$branch
fi

ref="altcos/$arch/$branch"

if [ -z "$ALTCOS_ROOT" ]
then
    echo "Variable ALTCOS_ROOT must be defined" && exit 1
fi

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable STREAMS_ROOT must be defined" && exit 1
fi

branch_repo="$STREAMS_ROOT/$ref"
export IMAGEDIR="$branch_repo/mkimage-profiles"
mkdir -p "$IMAGEDIR" || exit 1
chmod 777 "$IMAGEDIR"

if [ -z "$MKIMAGE_PROFILES_ROOT" ]
then
    echo "Variable MKIMAGE_PROFILES_ROOT must be defined" && exit 1
fi

apt_dir="$HOME/apt"
if [ ! "$apt_dir" ]
then
    mkdir -p "$apt_dir" || exit 1
fi

if [ ! -f "$apt_dir/lists/partial" ]
then
    mkdir -p "$apt_dir/lists/partial" || exit 1
fi

if [ ! -f "$apt_dir/cache/$branch/archives/partial" ]
then
    mkdir -p "$apt_dir/cache/$branch/archives/partial" || exit 1
fi

if [ ! -d "$apt_dir/$arch/RPMS.dir" ]
then
    mkdir -p "$apt_dir/$arch/RPMS.dir"
fi

cat <<EOF > "$apt_dir"/apt.conf."$branch"."$arch"
Dir::Etc::SourceList "$apt_dir/sources.list.$branch.$arch";
Dir::Etc::SourceParts /var/empty;
Dir::Etc::main "/dev/null";
Dir::Etc::parts "/var/empty";
APT::Architecture "64";
Dir::State::lists "$apt_dir/lists/";
Dir::Cache "$apt_dir/cache/$branch/";
EOF

#cat <<EOF > "$apt_dir"/sources.list."$branch"."$arch"
#rpm [$ns] http://ftp.altlinux.org/pub/distributions/ALTLinux/ $pkg_repo_branch/$arch classic
#rpm [$ns] http://ftp.altlinux.org/pub/distributions/ALTLinux/ $pkg_repo_branch/noarch classic
#rpm-dir file:$apt_dir $arch dir
#EOF

cat <<EOF > "$apt_dir"/sources.list."$branch"."$arch"
rpm [$ns] http://mirror.yandex.ru/altlinux $pkg_repo_branch/$arch classic
rpm [$ns] http://mirror.yandex.ru/altlinux $pkg_repo_branch/noarch classic
rpm-dir file:$apt_dir $arch dir
EOF

cd "$MKIMAGE_PROFILES_ROOT" || exit 1

make DEBUG=1 APTCONF="$apt_dir"/apt.conf."$branch"."$arch" BRANCH="$branch" ARCH="$arch" vm/acos.tar
