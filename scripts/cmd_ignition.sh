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

check_commands "butane" "/usr/lib/dracut/modules.d/30ignition/ignition"

ref_dir=$1
root_dir=$2
butane_file="/tmp/$$.btn"
ignition_file="/tmp/$$.ign"
sudo cat > $butane_file
sudo butane -p -d "$ref_dir" "$butane_file" | sudo tee "$ignition_file"

sudo /usr/lib/dracut/modules.d/30ignition/ignition \
    -platform file \
    --stage files \
    -config-cache "$ignition_file" \
    -root "$root_dir"

sudo chroot "$root_dir" systemctl preset-all --preset-mode=enable-only
