# eosio-node

Ubuntu 20.04 container with:

- `eosio` - v2.0.13
- `eosio-cdt` - v1.6.3 during install and v1.7.0 after
- `telos.contracts` compiled inside `/usr/opt/telos.contracts/contracts`
- `telos.evm` compiled inside `/usr/opt/telos.contracts/contracts`

#### build command (from project root dir)

    docker build --tag eosio:2.0.13-evm docker/eosio
