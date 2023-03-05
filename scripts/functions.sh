#!/usr/bin/env bash


# Split passwd file (/etc/passwd) into
# /usr/etc/passwd - home users password file (uid >= 500)
# /lib/passwd - system users password file (uid < 500)
function split_passwd() {
    from_pass=$1
    sys_pass=$2
    user_pass=$3

    >"$sys_pass"
    >"$user_pass"

    set -f

    ifs=$IFS

    exec < "$from_pass"
    while read line
    do
        IFS=:;set -- $line;IFS=$ifs

        user=$1
        uid=$3

        if [[ $uid -ge 500 || $user = "root" || $user = "systemd-network" ]]
        then
            echo "$line" >> "$user_pass"
        else
            echo "$line" >> "$sys_pass"
        fi
    done
}

# Split group file (/etc/group) into
# /usr/etc/group - home users group file (uid >= 500)
# /lib/group - system users group file (uid < 500)
function split_group() {
    from_group=$1
    sys_group=$2
    user_group=$3

    >$sys_group
    >$user_group

    set -f

    ifs=$IFS
    
    exec < "$from_group"
    while read line
    do
        IFS=:;set -- $line;IFS="$ifs"
        user=$1
        uid=$3
        if [[ $uid -ge 500 ||
              $user = "root" ||
              $user = "adm" ||
              $user = "wheel" ||
              $user = "systemd-network" ||
              $user = "systemd-journal" ||
              $user = "docker" ]]
        then
            echo "$line" >> "$user_group"
        else
            echo "$line" >> "$sys_group"
        fi
    done
}

function ref_repo_dir() {
    ref=$1
    ifs=$IFS
    IFS=/;set -- $ref;IFS="$ifs"
    os=$1;arch=$2;branch=$(echo "$3" | tr '[:upper:]' '[:lower:]')
    echo "$os/$arch/$branch"
}

function ref_to_dir() {
    ref=$1
    echo "$ref" | tr '[:upper:]' '[:lower:]'
}

function version_var_subdir() {
    version=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    ifs=$IFS
    IFS=.;set -- $version;IFS=$ifs
    date=$2;major=$3;minor=$4
    echo "$date/$major/$minor"
}

function full_commit_id() {
    if [ -z "$STREAMS_ROOT" ]
    then
        echo "Variable STREAMS_ROOT must be defined" && exit 1
    fi

    (
    ref_dir=$1
    short_commit_id=$2

    var_dir=$STREAMS_ROOT/$ref_dir/vars
    cd "$var_dir" || exit 1

    ids=$(ls -1dr "$short_commit_id"*)
    set -- "$ids"

    if [ $# = 0 ]
    then
        echo "Commit $short_commit_id not exists" >&2
        return
    fi

    if [ $# -gt 1 ]
    then
        echo "Commit $short_commit_id is ambiguous" >&2
        return
    fi

    echo "$1"
    )
}

function last_commit_id() {
    (
    ref_dir=$1

    if [ -z "$STREAMS_ROOT" ]
    then
        echo "Variable STREAMS_ROOT must be defined" || exit 1
    fi

    cd "$STREAMS_ROOT/$ref_dir/vars" && exit 1

    mask="????????????????????????????????????????????????????????????????"
    commit_id=$(ls -1tdr "$mask" | tail -1) && echo "$commit_id"
    )
}

function ref_stream() {
    ref=$1
    ref_dir=$(ref_to_dir "$ref")
    ifs=$IFS;IFS=/;set -- $ref_dir;IFS=$ifs
    shift;shift
    stream=$1
    echo "$stream"
}

function ref_version() {
    if [ -z "$STREAMS_ROOT" ]
    then
        echo "Variable STREAMS_ROOT must be defined" && exit 1
    fi

    (
    ref=$1
    commit_id=$2
    ref_repo_dir=$(ref_repo_dir "$ref")
    repo_bare_path="$STREAMS_ROOT/$ref_repo_dir/bare/repo"
    ret=$(ostree --repo="$repo_bare_path" show "$commit_id" --print-metadata-key=version | tr -d "'")
    echo "$ret"
    )
}

function is_base_ref() {
    ref=$1
    ifs=$IFS
    IFS=/;set -- $ref;IFS=$ifs
    if [ $# = 3 ]
    then
        return 0
    else
        return 1
    fi
}

function check_apt_dirs() {
    root_dir=$1
    sudo mkdir -p "$root_dir"/var/lib/apt/lists/partial "$root_dir"/var/lib/apt/prefetch/
    sudo mkdir -p "$root_dir"/var/cache/apt/archives/partial "$root_dir"/var/cache/apt/gensrclist "$root_dir"/var/cache/apt/genpkglist
    sudo chmod -R 770 "$root_dir"/var/cache/apt/
    sudo chmod -R g+s "$root_dir"/var/cache/apt/
    sudo chown root:rpm "$root_dir"/var/cache/apt/
}

function check_commands() {
    for arg in "${@}"
    do
        if ! command -v "$arg" &> /dev/null
        then
            echo "Command $arg not found"
            echo "apt-get install $arg" && exit 1
        fi
    done
}
