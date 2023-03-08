#!/usr/bin/env bash

if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable SCRIPTS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable $STREAMS_ROOT must be defined" && exit 1
fi

check_commands "ostree"

exec 2>&1

ref=$1
ref_repo_dir=$(ref_repo_dir "$ref")
ref_dir=$(ref_to_dir "$ref")

commit_id=$2
version=$(ref_version "$ref" "$commit_id")

next_version=$3
next_version_var_subdir=$(version_var_subdir "$next_version")

repo_bare_path="$STREAMS_ROOT/$ref_repo_dir/bare/repo"
ref_dir="$STREAMS_ROOT/$ref_dir"
roots_path="$ref_dir/roots"
vars_path="$ref_dir/vars"

add_metadata=
if ! is_base_ref "$ref"
then
    altcos_file="$ref_dir/altconf.yml"

    add_metadata=" --add-metadata-string=parent_commit_id=$commit_id"
    add_metadata="$add_metadata --add-metadata-string=parent_version=$version"
    altcos_file_mt=$(date -r "$altcos_file" +%s 2>/dev/null)
    add_metadata="$add_metadata --add-metadata-string=altcos_file_mt=$altcos_file_mt"
fi

cd "$roots_path" || exit 1
new_commit_id=$(sudo ostree commit \
            --repo="$repo_bare_path" \
            --tree=dir="$commit_id" \
            -b "$ref" \
            --no-bindings \
            --mode-ro-executables \
            "$add_metadata" \
            --add-metadata-string=version="$next_version") || exit 1

sudo ostree summary --repo="$repo_bare_path" --update

sudo rm -rf "$commit_id"
cd "$vars_path" || exit 1
sudo ln -sf "$next_version_var_subdir" "$new_commit_id"
echo "$new_commit_id"