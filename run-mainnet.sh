#!/bin/bash

tevmc clean
tevmc pull --headless

tevmc config \
            --hyperion-cfg-path=docker/hyperion/config/chains/telos-mainnet.config.json \
            --indexer-start-on=180635436 \
            --index-only-evm

tevmc build --headless

tevmc up \
    --loglevel=info \
    --chain-name=telos-mainnet \
    --snapshot=/root/snapshots/snapshot-mainnet-20211026-blk-180635436.bin

tevmc wait-init

printf '\n\n\nTEVM mainnet up, run `tevmc down` to stop.\n\n\n'
