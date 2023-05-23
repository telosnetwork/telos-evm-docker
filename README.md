# telos-evm-docker
## Docker containers for local EVM development and building automated tests

## Overview

## Background Service Containers

### redis
### elasticsearch
### kibana
### filebeats

## Data pipeline

### nodeos container
The Telos node container, this is a local Telos native network on which the TelosEVM contract is deployed

### telosevm-translator & telos-evm-rpc
This piece of software consumes the `nodeos` websocket and produces EVM data that the `telos-evm-rpc`
container can consume to serve the ethereum compatible API.

## Dependencies
You will need `docker` & `python3`.

#### small python heads up

It's good practice to not modify the python envoirment that comes with the system, as it is sometimes used for system scripts.
A good practice is to use a virtual envoirment:

    1. linux: https://mothergeo-py.readthedocs.io/en/latest/development/how-to/venv.html
    2. windows:https://mothergeo-py.readthedocs.io/en/latest/development/how-to/venv-win.html


To install python dependencies:

    pip install -U --no-cache-dir -e . -r requirements.txt

If in your system you have both a `python` and `python3` binary, corresponding to `python2.7` and `python3.x`
respectively. You'll need to specify which version of `pip` to use:

    pip3 install -U --no-cache-dir -e . -r requirements.txt

Or if not found:

    python3 -m pip install -U --no-cache-dir -e . -r requirements.txt

## Execution
    tevmc init local
    cd local
    tevmc build
    tevmc up
    tevmc stream daemon

## Important data

- The chain_id of the TelosEVM network is 41 and as hex `0x29`
- The endpoint for the TelosEVM RPC will be http://localhost:7000/evm
- Inside the TelosEVM is an account ready to use with 100M TLOS, it's info is:
    - Explorer link http://localhost:7000/v2/explore/evm/address/0xf79b834a37f3143f4a73fc3934edac67fd3a01cd
    - Address `0xf79b834a37f3143f4a73fc3934edac67fd3a01cd`
    - Private key `0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d`
- There are also 10 other accounts with 10k TLOS each which can be used in truffle tests, see the `test_erc20/truffle-config.js` file for an example, their full details are also in `accounts.json`
- The chain_id of the Telos native network is `c4c5fcc7b6e5e7484eb6b609e755050ebba977c4c291a63aab42d94c0fb8c2cf`
- The Telos native http RPC is available at http://localhost:8888
- The `eosio` superuser account for the Telos native has the following keypair for both active and owner:
  - Public: `EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L`
  - Private: `5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL`
- You can access kibana at http://localhost:5601/ with username `elastic` and password `password`

## Running Tests

With all containers up, tests can be run using [truffle](https://www.trufflesuite.com/docs/truffle/testing/writing-tests-in-solidity):

```
cd telos-evm-docker/tests/test_erc20/
truffle test --network private --verbose-rpc
```
