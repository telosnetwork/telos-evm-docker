#!/usr/bin/env bash
set -o errexit

# set PATH
PATH="$PATH:/opt/eosio/bin"

CONTRACTSPATH="$( pwd -P )/contracts"

# make new directory for compiled contract files
mkdir -p ./compiled_contracts
mkdir -p ./compiled_contracts/$1

COMPILEDCONTRACTSPATH="$( pwd -P )/compiled_contracts"

# unlock the wallet, ignore error if already unlocked
if [ ! -z $3 ]; then cleos wallet unlock -n $3 --password $4 || true; fi

# compile smart contract to wasm and abi files using EOSIO.CDT (Contract Development Toolkit)
# https://github.com/EOSIO/eosio.cdt
if [ ! -f "$CONTRACTSPATH/$1/$1.wasm" ]; then
  eosio-cpp -abigen "$CONTRACTSPATH/$1/$1.cpp" -o "$COMPILEDCONTRACTSPATH/$1/$1.wasm" --contract "$1"
else
  cp "$CONTRACTSPATH/$1/$1.wasm" "$COMPILEDCONTRACTSPATH/$1/$1.wasm"
  cp "$CONTRACTSPATH/$1/$1.abi" "$COMPILEDCONTRACTSPATH/$1/$1.abi"
fi

echo "ls $COMPILEDCONTRACTSPATH/$1:"
ls $COMPILEDCONTRACTSPATH/$1

if $5 ; then
  # set (deploy) compiled contract to blockchain
  #echo "running: cleos -v --print-response set contract $2 "$COMPILEDCONTRACTSPATH/$1/" --permission $2"
  #cleos -v --print-response set contract $2 "$COMPILEDCONTRACTSPATH/$1/" --permission $2
  echo "running: cleos set contract $2 "$COMPILEDCONTRACTSPATH/$1/" --permission $2"
  cleos set contract $2 "$COMPILEDCONTRACTSPATH/$1/" --permission $2
  echo "contract set"
fi
