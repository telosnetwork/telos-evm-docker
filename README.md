# telos-evm-docker
## Docker container for local EVM development and building automated tests

## Execution
`./run.sh` will destroy the container (if it exists), build, and then run the container.

The container will bind to the localhost's 8888 for http RPC and 8080 for state-history, you can run cleos and it will then default to the container

## Important data

- The chain_id of the Telos native network is `c4c5fcc7b6e5e7484eb6b609e755050ebba977c4c291a63aab42d94c0fb8c2cf`
- The chain_id of the TelosEVM network is 41 and as hex `0x29`
- The `eosio` superuser account for the Telos native has the following keypair for both active and owner:
  - Public: `EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L`
  - Private: `5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL`
- Inside the TelosEVM is an account ready to use with 10k TLOS, it's info is:
    - Address `0xf79b834a37f3143f4a73fc3934edac67fd3a01cd`
    - Private key `0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d`

