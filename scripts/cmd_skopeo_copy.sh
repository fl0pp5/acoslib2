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

merge_dir=$1
shift
docker_images_dir="$merge_dir/usr/dockerImages"
if [ ! -d "$docker_images_dir" ]
then
    sudo mkdir -p "$docker_images_dir"
fi

tmpfile="/tmp/skopeo.$$"
for image
do
    archive_file=$(echo $image | tr '/' '_' | tr ':' '_')
    archive_file=$docker_images_dir/$archive_file
    sudo rm -rf "$archive_file"

    xzfile="$archive_file.xz"
    if [ ! -f "$xzfile" ]
    then
        >$tmpfile
        until grep manifest $tmpfile
        do
            sudo rm -f "$archive_file"
            sudo skopeo copy --additional-tag=$image docker://$image docker-archive:$archive_file  2>&1 | tee $tmpfile
        done
        sudo xz -9 "$archive_file"
    fi
done

rm -f $tmpfile
date
