FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget \
        ca-certificates

# install system contracts
COPY contracts /opt/eosio/bin/contracts

WORKDIR /root

RUN wget https://github.com/EOSIO/eos/releases/download/v2.1.0/eosio_2.1.0-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio_2.1.0-1-ubuntu-18.04_amd64.deb && \
    rm -rf *.deb

COPY snapshots ./snapshots

# final configuration
COPY config.local.ini ./config.local.ini
COPY config.testnet.ini ./config.testnet.ini
COPY config.mainnet.ini ./config.mainnet.ini

COPY genesis.local.json ./genesis.local.json
COPY genesis.testnet.json ./genesis.testnet.json
COPY genesis.mainnet.json ./genesis.mainnet.json

COPY keosd_config.ini ./eosio-wallet/config.ini

EXPOSE 8888
