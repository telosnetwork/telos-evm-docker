#!/usr/bin/env bash
set -o errexit

logInfo() {
  echo "============="
  echo -e "INIT BLOCKCHAIN :: $@"
  echo "============="
}

logInfo "creating blockchain accounts and deploying smart contract"

# set PATH
PATH="$PATH:/opt/eosio/bin:/opt/eosio/bin/scripts"

# sourcing variable from config file
source ./scripts/config.file

# override config if there are any local config changes
if [ -f "./scripts/config.file.local" ]; then
  source ./scripts/config.file.local
fi

# set contracts path
CONTRACTSPATH="$( pwd -P )/contracts"

set -m

touch /mnt/dev/data/nodeos.log
# start nodeos ( local node of blockchain )
# run it in a background job such that docker run could continue
nodeos -e -p eosio -d /mnt/dev/data \
  --config-dir /mnt/dev/config \
  --disable-replay-opts \
  --genesis-json "./scripts/genesis.json" >> /mnt/dev/data/nodeos.log 2>&1 &

tail -f /mnt/dev/data/nodeos.log &

# wait for blockchain to start
sleep 1s
until [ $(curl localhost:8888/v1/chain/get_info | jq -e '.head_block_num') -gt 4 ]
do
  sleep 1s
done

logInfo "create wallet: eosio"
# First key import is for eosio system account
cleos wallet create -n eosio --to-console | tail -1 | sed -e 's/^"//' -e 's/"$//' > eosio_wallet_password.txt
cleos wallet import -n eosio --private-key 5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL

# deploy bios contract, this is required in getABI for system contracts 
#deploy_contract.sh eosio.bios eosio eosio $(cat eosio_wallet_password.txt) true
logInfo "creating eosio accounts"
for i in eosio.token eosio.rex eosio.ram eosio.ramfee eosio.stake eosio.bpay eosio.vpay eosio.names eosio.saving eosio.trail; do
  cleos create account eosio $i EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L #--stake-net "10.0000 TLOS" --stake-cpu "10.0000 TLOS" --buy-ram "100.0000 TLOS"
done
logInfo "deploying eosio.token"
deploy_contract.sh eosio.token eosio.token eosio $(cat eosio_wallet_password.txt) true
cleos push action eosio.token create '["eosio", "100000000000.0000 TLOS"]' -p eosio.token@active
cleos push action eosio.token issue '[ "eosio", "1000000000.0000 TLOS", "memo" ]' -p eosio@active

logInfo "activating"
curl -X POST http://127.0.0.1:8888/v1/producer/schedule_protocol_feature_activations -d '{"protocol_features_to_activate": ["0ec7e080177b2c02b278d5088611686b49d739925a92d9bfcacd7fc6b74053bd"]}'

sleep 5

logInfo "deploying system contract"
deploy_contract.sh eosio.system eosio eosio $(cat eosio_wallet_password.txt) true
logInfo "initializing system contract"
cleos push action eosio init '[0, "4,TLOS"]' -p eosio@active

#'{"threshold":1,"keys":[],"accounts":[{"permission":{"actor":"eosio","permission":"active"},"weight":1}]}'


logInfo "creating eosio.evm"
cleos system newaccount eosio eosio.evm EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L  --stake-net "10.0000 TLOS" --stake-cpu "10.0000 TLOS" --buy-ram "10000.0000 TLOS"
cleos system newaccount eosio fees.evm EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L  --stake-net "10.0000 TLOS" --stake-cpu "10.0000 TLOS" --buy-ram "10000.0000 TLOS"
cleos push action eosio setpriv '["eosio.evm",1]' -p eosio@active

logInfo "creating rpc.evm"
cleos system newaccount eosio rpc.evm EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L --stake-net "10000.0000 TLOS" --stake-cpu "10000.0000 TLOS" --buy-ram "10000.0000 TLOS"

logInfo "creating evmuser1"
cleos system newaccount eosio evmuser1 EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L --stake-net "10.0000 TLOS" --stake-cpu "10.0000 TLOS" --buy-ram "10000.0000 TLOS"
cleos transfer eosio evmuser1 "111000000.0000 TLOS"

logInfo "deploying eosio.evm"
#deploy_contract.sh eosio.evm eosio.evm eosio $(cat eosio_wallet_password.txt) true
node /opt/eosio/bin/scripts/deployEvm.js $DEBUG_EVM

# cleos set account permission eosio active EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L owner -p eosio@owner
# cleos set account permission eosio owner EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L -p eosio@owner

logInfo "end of setting up blockchain accounts and smart contract"

# create a file to indicate the blockchain has been initialized
touch "/mnt/dev/data/initialized"

# put the background nodeos job to foreground for docker run
fg %1
