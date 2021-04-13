#!/bin/bash

INSTALL_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker network create -d bridge docker_hyperion
$INSTALL_ROOT/remove_eosio_docker.sh
$INSTALL_ROOT/build_eosio_docker.sh
$INSTALL_ROOT/start_eosio_docker.sh
