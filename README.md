# telos-evm-docker
## Docker containers for local EVM development and building automated tests

## Overview
### eosio_nodeos container
The Telos node container, this is a local Telos native network on which the TelosEVM contract is deployed

### hyperion containers
Hyperion is a powerful history solution that powers much of the apps and block explorers for Telos.  The TelosEVM RPC is built as a plugin for Hyperion and there is a built in block explorer for Hyperion as well, which supports viewing EVM transactions and address history.

Hyperion is composed of the following containers:
- redis for API request caching
- rabbitmq for queueing history data before it is indexed into...
- elastic search which has full history for transactions
- kibana is the UI for elastic
- hyperion-indexer reads historical data from the Telos node via websocket and writes events to rabbitmq
- hyperion-api serves the TelosEVM RPC, block explorer, swagger UI and satisfies any API requests

## Dependencies
You will need `docker`, `docker-compose` and `jq` installed.

## Execution
`./run.sh debug` will destroy the containers (if they exist), build, and then run the containers.

## Important data

- The chain_id of the TelosEVM network is 41 and as hex `0x29`
- The endpoint for the TelosEVM RPC will be http://localhost:7000/evm
- The block explorer will be accessible at http://localhost:7000/v2/explore
- Inside the TelosEVM is an account ready to use with 100M TLOS, it's info is:
    - Explorer link http://localhost:7000/v2/explore/evm/address/0xf79b834a37f3143f4a73fc3934edac67fd3a01cd
    - Address `0xf79b834a37f3143f4a73fc3934edac67fd3a01cd`
    - Private key `0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d`
- There are also 10 other accounts with 10k TLOS each which can be used in truffle tests, see the `test_erc20/truffle-config.js` file for an example, their full details are also in `accounts.json`
- The chain_id of the Telos native network is `c4c5fcc7b6e5e7484eb6b609e755050ebba977c4c291a63aab42d94c0fb8c2cf`
- The Telos native http RPC is available at http://localhost:8888
- The Telos native state-history websocket endpoint is available at http://localhost:8080 (this is required for hyperion to stream blockchain history from)
- The `eosio` superuser account for the Telos native has the following keypair for both active and owner:
  - Public: `EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L`
  - Private: `5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL`
- The Swagger UI will be accessible at http://localhost:7000/v2/docs/static/index.html
- You can access kibana at http://localhost:5601/ with username `elastic` and password `password`
- You can access rabbitmq at http://localhost:15672/ with username `username` and password `password`
