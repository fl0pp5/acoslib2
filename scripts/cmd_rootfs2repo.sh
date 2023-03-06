#!/usr/bin/env bash


if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable STREAMS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1


if [ "$UID" != 0 ]
then
    echo "ERROR: $0 needs to be run as root (uid=0) only" && exit 1
fi

check_commands "dracut" "ostree"


branch=${1:-altcos/x86_64/sisyphus}
branch_repo=$STREAMS_ROOT/$branch
rootfs_archive="${2:-$branch_repo/mkimage-profiles/acos-latest-x86_64.tar}"
main_repo="${3:-$branch_repo/bare/repo}"
out_dir="${4:-$branch_repo/vars}"
stream=$(ref_stream $branch)

if [ ! -e $rootfs_archive ]
then
	echo "ERROR: Rootfs archive must exist ($rootfs_archive)"
	exit 1
fi

[ -L $rootfs_archive ] && rootfs_archive=$(realpath $rootfs_archive)

version_date=$(basename $rootfs_archive | awk -F- '{print $2;}')
echo "Date for version: $version_date"

if ! [[ "$version_date" =~ ^[0-9]{8}$ ]]
then
	echo "ERROR: The name of the rootfs archive ($rootfs_archive) contains an incorrect date"
	exit 1
fi

data_dir=$out_dir/$version_date
if [[ -d "$data_dir" && -n "$(ls -1 "$data_dir" 2>/dev/null)" ]]
then
  let major=$(ls -1 "$data_dir" 2>/dev/null | sort -n | tail -1)+1
else
  major=0
fi


version_dir=$version_date/$major/0
version_full_dir=${out_dir}/$version_dir

if [ -d $version_full_dir ]
then
	echo "ERROR: Version for date $version_date already exists."
	echo "Try: rm -rf $version_full_dir"
	exit 1
fi
rm -rf $version_full_dir

mkdir --mode=0775 -p $version_full_dir

tmp_dir=$(mktemp --tmpdir -d rootfs_to_repo-XXXXXX)
main_root=$tmp_dir/root

mkdir --mode=0775 -p $main_root
tar xf $rootfs_archive -C $main_root --exclude=./dev/tty --exclude=./dev/tty0 --exclude=./dev/console  --exclude=./dev/urandom --exclude=./dev/random --exclude=./dev/full --exclude=./dev/zero --exclude=/dev/null --exclude=./dev/pts/ptmx --exclude=./dev/null

#Вынести в m-i-p
rm -f $main_root/etc/resolv.conf
ln -sf /run/systemd/resolve/resolv.conf $main_root/etc/resolv.conf

rpms_dir="/home/$SUDO_USER/apt/$branch"
if [ -d $rpms_dir ]
then
  apt-get update -y -o RPM::RootDir=$main_root
  apt-get install -y -o RPM::RootDir=$main_root $rpms_dir/*
fi

sed -i 's/^LABEL=ROOT\t/LABEL=boot\t/g' $main_root/etc/fstab
sed -i 's/^AcceptEnv /#AcceptEnv /g' $main_root/etc/openssh/sshd_config
sed -i 's/^# WHEEL_USERS ALL=(ALL) ALL$/WHEEL_USERS ALL=(ALL) ALL/g' $main_root/etc/sudoers
echo "zincati ALL=NOPASSWD: ALL" > $main_root/etc/sudoers.d/zincati
sed -i 's|^HOME=/home$|HOME=/var/home|g' $main_root/etc/default/useradd
echo "blacklist floppy" > $main_root/etc/modprobe.d/blacklist-floppy.conf
mkdir --mode=0775 $main_root/sysroot
ln -s sysroot/ostree $main_root/ostree

mv -f $main_root/home $main_root/opt $main_root/srv $main_root/mnt $main_root/var/
mv -f $main_root/root $main_root/var/roothome
mv -f $main_root/usr/local $main_root/var/usrlocal
ln -sf var/home $main_root/home
ln -sf var/opt $main_root/opt
ln -sf var/srv $main_root/srv
ln -sf var/roothome $main_root/root
ln -sf ../var/usrlocal $main_root/usr/local
ln -sf var/mnt $main_root/mnt

mkdir --mode=0775 -p $main_root/etc/ostree/remotes.d/
echo "
[remote \"altcos\"]
url=https://altcos.altlinux.org/ALTCOS/streams/$branch/archive/repo/
gpg-verify=false
" > $main_root/etc/ostree/remotes.d/altcos.conf
echo "
# ALTLinux CoreOS Cincinnati backend
[cincinnati]
base_url=\"https://altcos.altlinux.org\"
" > $main_root/etc/zincati/config.d/50-altcos-cincinnati.toml
echo "
[Match]
Name=eth0

[Network]
DHCP=yes
" > $main_root/etc/systemd/network/20-wired.network

sed -i -e 's|#AuthorizedKeysFile\(.*\)|AuthorizedKeysFile\1 .ssh/authorized_keys.d/ignition|' $main_root/etc/openssh/sshd_config

chroot $main_root groupadd altcos
chroot $main_root useradd -g altcos -G docker,wheel -d /var/home/altcos --create-home -s /bin/bash altcos

split_passwd $main_root/etc/passwd $main_root/lib/passwd /tmp/passwd.$$
mv /tmp/passwd.$$ $main_root/etc/passwd

split_group $main_root/etc/group $main_root/lib/group /tmp/group.$$
mv /tmp/group.$$ $main_root/etc/group

sed -e 's/passwd:.*$/& altfiles/' -e 's/group.*$/& altfiles/' -i $main_root/etc/nsswitch.conf

mv $main_root/var/lib/rpm $main_root/lib/rpm

kernel=$(find $main_root/boot/ -type f -name "vmlinuz-*")
sha=$(sha256sum "$kernel" | awk '{print $1;}')
mv "$kernel" "$kernel-$sha"
rm -f $main_root/boot/vmlinuz
rm -f $main_root/boot/initrd*

cat <<EOF > $main_root/ostree.conf
d /run/ostree 0755 root root -
f /run/ostree/initramfs-mount-var 0755 root root -
EOF
chroot $main_root dracut --reproducible --gzip -v --no-hostonly \
	-f /boot/initramfs-$sha \
	--add ignition --add ostree \
	--include /ostree.conf /etc/tmpfiles.d/ostree.conf \
	--include /etc/systemd/network/eth0.network /etc/systemd/network/eth0.network \
	--omit-drivers=floppy --omit=nfs --omit=lvm --omit=iscsi \
	--kver $(ls $main_root/lib/modules)

rm -f $main_root/ostree.conf
rm -rf $main_root/usr/etc
mv $main_root/etc $main_root/usr/etc

rsync -av $main_root/var $version_full_dir

rm -rf $main_root/var
mkdir $main_root/var

if [ ! -d $main_repo ]
then
	mkdir --mode=0775 -p $main_repo
	ostree init --repo=$main_repo --mode=bare
fi

commit_id=$(ostree commit --repo=$main_repo --tree=dir=$main_root -b $branch \
	--no-xattrs --no-bindings --mode-ro-executables \
	--add-metadata-string=version=$stream.$version_date.$major.0)

cd ${out_dir}
ln -sf $version_dir $commit_id
rm -rf $tmp_dir
