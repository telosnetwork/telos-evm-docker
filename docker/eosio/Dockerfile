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

# final configuration
COPY config.ini ./config.ini
COPY keosd_config.ini ./eosio-wallet/config.ini
COPY genesis.json ./genesis.json
EXPOSE 8888
