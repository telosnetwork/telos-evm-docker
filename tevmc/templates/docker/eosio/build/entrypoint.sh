#!/bin/bash

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

cmds="$cmds --disable-replay-opts"

echo "nodeos -e -p eosio ${cmds[@]} 2>&1" | tee -a ${NODEOS_LOG_PATH}

mkfifo stream

nodeos -e -p eosio ${cmds[@]} 2>&1 > stream &
nodeos_pid="$!"

echo $nodeos_pid
while read line <stream; do
    echo "$line" | tee -a ${NODEOS_LOG_PATH}
done
