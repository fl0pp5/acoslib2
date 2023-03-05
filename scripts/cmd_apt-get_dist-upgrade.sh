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
ref_dir=$(ref_to_dir $ref)
rpm_list_file=$2
roots_path=$STREAMS_ROOT/$ref_dir/roots
merged_dir=$roots_path/merged
check_apt_dirs $merged_dir

sudo chroot $merged_dir apt-get dist-upgrade -y -o RPM::DBPath='/lib/rpm'
sudo chroot $merged_dir rpm -qa --dbpath=/lib/rpm > $rpm_list_file
