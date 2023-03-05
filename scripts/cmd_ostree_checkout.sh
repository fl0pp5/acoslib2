#!/usr/bin/env bash


if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable SCRIPTS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable STREAMS_ROOT must be defined" && exit 1
fi

check_commands "ostree"

exec 2>&1

ref=$1
last_commit_id=$2
to_ref=$3
clear=$4

ref_repo_dir=$(ref_repo_dir "$ref")
branch_repo_path="$STREAMS_ROOT/$ref_repo_dir"
repo_bare_path="$branch_repo_path/bare/repo"

ref_dir=$(ref_to_dir "$ref")
branch_path="$STREAMS_ROOT/$ref_dir"
var_dir="$branch_path/vars/$last_commit_id"
if [ -n "$to_ref" ]
then
    ref_to_dir=$(ref_to_dir "$to_ref")
    branch_path="$STREAMS_ROOT/$ref_to_dir"
fi

roots_path="$branch_path/roots"
roots_path_old="$branch_path/rootsi.$$"

if [ ! -d "$var_dir" ]
then
    echo "var directory $var_dir not exists" && exit 1
fi

if [ "$clear" = 'all' ]
then
    sudo mv "$roots_path" "$roots_path_old"
    sudo umount "$roots_path_old/merged"
    sudo rm -rf "$roots_path_old"
fi
sudo mkdir -p "$roots_path" || exit 1
cd "$roots_path" || exit 1

if [ ! -d "$last_commit_id" ]
then
    sudo ostree checkout --repo "$repo_bare_path" "$last_commit_id"
fi
sudo ln -sf "$last_commit_id" root

while sudo umount ./merged; do :; done

for dir in merged upper work
do
    if [ -d "$dir" ]
    then
        sudo rm -rf "$dir"
    fi
    sudo mkdir "$dir"
done

sudo mount -t overlay overlay -o lowerdir="$last_commit_id",upperdir=./upper,workdir=./work ./merged

cd merged || exit 1
sudo ln -sf /usr/etc ./etc
sudo rsync -a "$var_dir"/var .
sudo mkdir -p ./run/lick ./run/systemd/resolve ./tmp/.private/root
sudo cp /etc/resolv.conf ./run/systemd/resolve/resolv.conf
