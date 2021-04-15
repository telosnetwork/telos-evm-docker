#!/bin/bash

INSTALL_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker network create -d bridge docker_hyperion
$INSTALL_ROOT/remove_eosio_docker.sh
$INSTALL_ROOT/build_eosio_docker.sh
$INSTALL_ROOT/start_eosio_docker.sh

echo "sleeping for 30sec so nodeos can startup..."
sleep 30
retcode=1
contract_deployed="false"

for i in $(seq 1 20); do
    code=$(curl -X POST  -d '{"account_name": "eosio.evm", "code_as_wasm": 1}' -H 'Content-Type: application/json' http://localhost:8888/v1/chain/get_code | jq -e '.code_hash' | tr -d '"')
    if [ ${#code} -ge 60 ] && [ "$code" != "0000000000000000000000000000000000000000000000000000000000000000" ]; then
        echo "EVM contract deployed!!"
        contract_deployed="true"
        break;
    fi
    echo "EVM not yet deployed, waiting..."
    sleep 2
done

cd $INSTALL_ROOT/hyperion/docker
./scripts/stop.sh
./scripts/clean-up.sh
./scripts/start.sh
