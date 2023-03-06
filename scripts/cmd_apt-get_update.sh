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
#sudo sed -i -e 's/#rpm \[alt\] http/rpm [alt] http/' "$merge_dir"/usr/etc/apt/sources.list.d/alt.list
(echo 'rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/x86_64 classic'
echo 'rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/noarch classic'
echo 'rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/x86_64-i586 classic') | sudo tee -a "$merge_dir"/usr/etc/apt/sources.list.d/alt.list

#cat <<EOF > "$merge_dir"/usr/etc/apt/sources.list.d/alt.list
#rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/x86_64 classic
#rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/noarch classic
#rpm [alt] http://mirror.yandex.ru/altlinux Sisyphus/x86_64-i586 classic
#EOF

sudo chroot "$merge_dir" apt-get update -o RPM::DBPath='/lib/rpm/'