#!/usr/bin/env bash

if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable SCRIPTS_ROOT must be defined" && exit 1
fi

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable $STREAMS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1

exec 2>&1
ref=$1
ref_dir=$(ref_to_dir "$ref")
commit_id=$2
version=$3

version_var_subdir=$(version_var_subdir $version)
branch_path="$STREAMS_ROOT/$ref_dir"
roots_path="$branch_path/roots"
commit_path="$roots_path/root"
var_dir="$branch_path/vars/$version_var_subdir"

cd "$roots_path" || exit 1
sudo du -s upper
sudo du -s root
sudo rm -f ./upper/etc ./root/etc

sudo mkdir --mode=0775 -p "$var_dir"
cd upper || exit 1

sudo rm -rf ./var/lib/apt ./var/cache/apt
check_apt_dirs "$PWD"

sudo rsync -av var "$var_dir"
sudo rsync -avd var/lib/rpm usr/share
sudo rm -rf ./var ./run
sudo mkdir ./var

delete=$(sudo find . -type c)
sudo rm -rf "$delete"

cd "$commit_path" || exit 1
sudo rm -rf "$delete"
cd ../upper || exit 1
sudo find . -depth | (cd ../merged;sudo cpio -plmdu "$commit_path"/) 2>/tmp/sync_updates.log

cd ..
sudo du -s upper
sudo du -s root
sudo umount merged
