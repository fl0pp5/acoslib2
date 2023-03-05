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
branch_path="$STREAMS_ROOT/$ref_dir"
roots_dir="$branch_path/roots"

cd $roots_dir

mask="????????????????????????????????????????????????????????????????"

sudo rm -rf $mask merged upper root work
