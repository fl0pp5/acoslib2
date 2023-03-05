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

exec 2>&1

ref=$1
ref_dir=$(ref_to_dir $ref)

# rpm_list_file=$2
roots_path="$STREAMS_ROOT/$ref_dir/roots";
merged_dir=$roots_path/merged
sudo chroot $merged_dir rm -rf /var/lib/rpm
sudo chroot $merged_dir ln -sf /lib/rpm/ /var/lib/
sudo chroot $merged_dir apt-get install -y update-kernel
sudo chroot $merged_dir update-kernel -y
sudo chroot $merged_dir apt-get remove -y update-kernel
