#!/bin/bash

INSTALL_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

$INSTALL_ROOT/remove_eosio_docker.sh
$INSTALL_ROOT/build_eosio_docker.sh
$INSTALL_ROOT/start_eosio_docker.sh
