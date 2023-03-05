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

check_commands "qemu-img" "ostree"

root_size=20GiB

exec 2>&1

if [ $# -gt 4 ]
then
	echo "Help: $0 [<branch>] [<commitid> or <vardir>] [<directory of main ostree repository>] [<out_file>]"
	echo "For example: $0  altcos/x86_64/sisyphus ac24e repo out/1.qcow2  "
	echo "For example: $0  altcos/x86_64/sisyphus out/var repo out/1.qcow2  "
	echo "You can change TMPDIR environment variable to set another directory where temporary files will be stored"
	exit 1
fi

if [ "$UID" != 0 ]
then
    echo "ERROR: $0 needs to be run as root (uid=0) only" && exit 1
fi

# Set branch variables
branch=${1:-altcos/x86_64/sisyphus}
branch_repo_dir=$(ref_repo_dir $branch)
branch_repo=$STREAMS_ROOT/$branch_repo_dir
main_repo=${3:-$branch_repo/bare/repo}
if [ ! -d $main_repo ]
then
	echo "ERROR: ostree repository must exist"
	exit 1
fi
ref_dir=$(ref_to_dir $branch)
branch_dir=$STREAMS_ROOT/$ref_dir
if [ ! -d  $branch_dir ]
then
  mkdir -m 0775 -p $branch_dir
fi

# Set Commit variables
short_commit_id=$2
if [ -z $short_commit_id ]
then
  commit_id=$(last_commit_id $ref_dir)
  var_dir=$branch_repo/vars/$commit_id/var
else
  if [[ "$short_commit_id" == */* ]] # It's var_dir
  then
    var_dir=$short_commit_id
  else
    commit_id=$(full_commit_id $ref_dir $short_commit_id)
    var_dir=$branch_dir/vars/$commit_id/var
  fi
fi

if [ -z "$commit_id" ]
then
  echo "ERROR: Commit $short_commit_id must exist"
  exit 1
fi


out_file=$4
if [ -z "$out_file" ]
then
  image_dir="$branch_dir/images"
  if [ ! -d $image_dir ]
  then
    mkdir -m 0775 -p $image_dir
  fi
  out_dir="$image_dir/qcow2"
  if [ ! -d $out_dir ]
  then
    mkdir -m 0775 -p $out_dir
  fi
  out_filename=$(ref_version $branch $commit_id)
  out_file="$out_dir/$out_filename.qcow2"
fi

os_name=alt-containeros

mount_dir=$(mktemp --tmpdir -d altcos_make_qcow2-XXXXXX)
repo_local=$mount_dir/ostree/repo
raw_file=$(mktemp --tmpdir altcos_make_qcow2-XXXXXX.raw)

fallocate -l $root_size $raw_file

loop_dev=$(losetup --show -f $raw_file)
loop_part="$loop_dev"p1

dd if=/dev/zero of=$loop_dev bs=1M count=3
parted $loop_dev mktable msdos
parted -a optimal $loop_dev mkpart primary ext4 2MIB 100%
parted $loop_dev set 1 boot on
mkfs.ext4 -L boot $loop_part

mount $loop_part $mount_dir
ostree admin init-fs --modern $mount_dir
ostree pull-local --repo $repo_local $main_repo $commit_id
grub-install --target=i386-pc --root-directory=$mount_dir $loop_dev
ln -s ../loader/grub.cfg $mount_dir/boot/grub/grub.cfg
ostree config --repo $repo_local set sysroot.bootloader grub2
ostree config --repo $repo_local set sysroot.readonly true
ostree refs --repo $repo_local --create altcos:$branch $commit_id
ostree admin os-init $os_name --sysroot $mount_dir

OSTREE_BOOT_PARTITION="/boot" ostree admin deploy altcos:$branch --sysroot $mount_dir --os $os_name \
	--karg-append=ignition.platform.id=qemu --karg-append=\$ignition_firstboot \
	--karg-append=net.ifnames=0 --karg-append=biosdevname=0 \
	--karg-append=rw \
	--karg-append=quiet --karg-append=root=UUID=$(blkid --match-tag UUID -o value $loop_part)

rm -rf $mount_dir/ostree/deploy/$os_name/var
rsync -av $var_dir $mount_dir/ostree/deploy/$os_name/
touch $mount_dir/ostree/deploy/$os_name/var/.ostree-selabeled

touch $mount_dir/boot/ignition.firstboot

umount $mount_dir
rm -rf $mount_dir
losetup --detach "$loop_dev"
qemu-img convert -O qcow2 $raw_file $out_file
rm $raw_file

echo $out_file
#read -p "Create compressed image (several minutes) (y/n)? " -n 1 -r
#echo
#[[ $REPLY =~ ^[Yy]$ ]] || exit 0
#
#image_dirname=$(dirname $out_file)
#xzfile=$(basename $out_file)
#tmpfile="/tmp/$xzfile.xz"
#xz -9v < $out_file > $tmpfile
#mv $tmpfile $image_dirname

