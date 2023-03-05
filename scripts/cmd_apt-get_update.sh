#!/usr/bin/env bash

exec 2>&1

if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable SCRIPTS_ROOT must be defined" && exit 1
fi

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable $STREAMS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1

ref=$1
ref_dir=$(ref_to_dir "$ref")

roots_path="$STREAMS_ROOT/$ref_dir/roots"
merge_dir="$roots_path/merged"
check_apt_dirs "$merge_dir"
sudo sed -i -e 's/#rpm \[alt\] http/rpm [alt] http/' "$merge_dir"/usr/etc/apt/sources.list.d/alt.list
sudo chroot "$merge_dir" apt-get update -o RPM::DBPath='/lib/rpm/'