#!/bin/bash

trap exit INT

# launch nodeos
genesis="${NODEOS_GENESIS_JSON}"
snapshot="${NODEOS_SNAPSHOT}"
logconf="${NODEOS_LOGCONF}"

cmds="--data-dir=${NODEOS_DATA_DIR} --config=${NODEOS_CONFIG}"

if [ ! -z "$genesis" ]; then
    cmds="$cmds --genesis-json=$genesis"
fi

if [ ! -z "$snapshot" ]; then
    cmds="$cmds --snapshot=$snapshot"
fi

if [ ! -z "$logconf" ]; then
    cmds="$cmds --logconf=$logconf"
fi

echo $cmds

nodeos -e -p eosio --disable-replay-opts ${cmds[@]} 2>&1 |
while read line; do
    echo $line >> "${NODEOS_LOG_PATH}"
done
