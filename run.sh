#!/bin/bash

set -e

INSTALL_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker network create -d bridge docker_hyperion 2>/dev/null || true
$INSTALL_ROOT/remove_eosio_docker.sh
$INSTALL_ROOT/build_eosio_docker.sh
$INSTALL_ROOT/start_eosio_docker.sh $1

retcode=1
contract_deployed="false"

for i in $(seq 1 30); do
    code=$(curl -s -X POST  -d '{"account_name": "eosio.evm", "code_as_wasm": 1}' -H 'Content-Type: application/json' http://localhost:8888/v1/chain/get_code | jq -e '.code_hash' | tr -d '"')
    if [ ${#code} -ge 60 ] && [ "$code" != "0000000000000000000000000000000000000000000000000000000000000000" ]; then
        echo "EVM contract deployed!!"
        contract_deployed="true"
        break;
    fi
    echo "EVM not yet deployed, waiting..."
    sleep 3
done

if [ "$contract_deployed" != "true" ]; then
    echo "Failure - Exceeded time waiting for Telos node to start and EVM contract to be deployed"
    exit 1
fi

cd $INSTALL_ROOT/hyperion/docker
./scripts/stop.sh
./scripts/clean-up.sh
./scripts/start.sh

indexing_complete=false
for i in $(seq 1 30); do
    actions=$(curl -s http://127.0.0.1:7000/v2/history/get_actions?account=eosio.evm | jq -e '.actions | length')
    if [ ! -z "$actions" ] && [ $actions -ge 1 ]; then
        echo "Indexing complete!"
        indexing_complete=true
        break;
    fi
    echo "Indexing has not begun, waiting..."
    sleep 3
done

if  [ "$indexing_complete" != "true" ]; then
    echo "ERROR: Failed to start indexing"
fi