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

# install snapshots from latest evm deployments
RUN mkdir /root/snapshots
WORKDIR /root/snapshots
RUN wget https://telos-snapshots.s3.amazonaws.com/testnet/telos-testnet-20211020-blknum-136229794.tar.gz &&\
    tar xvf telos-testnet-20211020-blknum-136229794.tar.gz && \
    mv \
        snapshot-081eb3a22f5d3aeb348599b02f3afdd31adc36f278b0fbaba60441608015d58f.bin \
        snapshot-testnet-20211020-blknum-136229794.bin

RUN wget https://telos-snapshots.s3.amazonaws.com/mainnet/telos-mainet-20211026-blk-180635436.tar.gz && \
    tar xvf telos-mainet-20211026-blk-180635436.tar.gz && \
    mv \
        snapshot-0ac4472c3af648291761dad85c9090333474a733dd1852008e2d1d41b212a0fc.bin \
        snapshot-mainnet-20211026-blk-180635436.bin

WORKDIR /root

RUN wget https://github.com/EOSIO/eos/releases/download/v2.1.0/eosio_2.1.0-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio_2.1.0-1-ubuntu-18.04_amd64.deb && \
    rm -rf *.deb


# final configuration
COPY config.local.ini ./config.local.ini
COPY config.testnet.ini ./config.testnet.ini
COPY config.mainnet.ini ./config.mainnet.ini

COPY genesis.local.json ./genesis.local.json
COPY genesis.testnet.json ./genesis.testnet.json
COPY genesis.mainnet.json ./genesis.mainnet.json

COPY keosd_config.ini ./eosio-wallet/config.ini

EXPOSE 8888
