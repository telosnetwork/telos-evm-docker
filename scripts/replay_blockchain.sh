#!/usr/bin/env bash
set -o errexit

# this file is used to continue the stopped blockchain

echo "new replaying blockchain"

# set PATH
PATH="$PATH:/opt/eosio/bin:/opt/eosio/bin/scripts"

# sourcing variable from config file
source ./scripts/config.file

# override config if there are any local config changes
if [ -f "./scripts/config.file.local" ]; then
  source ./scripts/config.file.local
fi

set -m

# start nodeos ( local node of blockchain )
# run it in a background job such that docker run could continue
nodeos -e -p eosio -d /mnt/dev/data \
  --config-dir /mnt/dev/config \
  --disable-replay-opt \
  --hard-replay-blockchain \
  --genesis-json "./scripts/genesis.json" &

# `--hard-replay` option is needed
# because the docker stop signal is not being passed to nodeos process directly
# as we run the init_blockchain.sh as PID 1.

# put the background nodeos job to foreground for docker run
fg %1
