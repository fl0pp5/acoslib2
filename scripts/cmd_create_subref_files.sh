#!/usr/bin/env bash

set -x

if [ -z "$SCRIPTS_ROOT" ]
then
    echo "Variable SCRIPTS_ROOT must be defined" && exit 1
fi

if [ -z "$STREAMS_ROOT" ]
then
    echo "Variable $STREAMS_ROOT must be defined" && exit 1
fi

source "$SCRIPTS_ROOT"/functions.sh || exit 1

subref_dir=$1
source_altconf=$2
source_root_dir=$3


if [ -z "$subref_dir" ]
then
    echo "subref_dir argument is required" && exit 1
fi

mkdir -p "$STREAMS_ROOT/$subref_dir" || exit 1

if [ -n "$source_altconf" ]
then
    cp "$source_altconf" "$STREAMS_ROOT/$subref_dir/altcos.yml" || exit 1
fi

if [ -n "$source_root_dir" ]
then
    cp -r "$source_root_dir" "$STREAMS_ROOT/$subref_dir/root" || exit 1
fi

