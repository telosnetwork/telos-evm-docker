FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/eosio/bin/

RUN apt-get update && apt-get install -y wget sudo curl git jq

RUN curl -sL https://deb.nodesource.com/setup_16.x | sudo bash - && \
    apt-get install -yq nodejs build-essential

RUN wget https://github.com/EOSIO/eosio.cdt/releases/download/v1.6.3/eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb

RUN wget https://github.com/EOSIO/eos/releases/download/v2.1.0/eosio_2.1.0-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio_2.1.0-1-ubuntu-18.04_amd64.deb

RUN npm install -g truffle

WORKDIR /root/scripts

RUN npm install \
    node-fetch@"<3.0.0" \
    @telosnetwork/telosevm-js@0.1.1-18

WORKDIR /root/tests

RUN npm install \
    eos-evm-js \
    node-fetch@"<3.0.0" \
    @truffle/hdwallet-provider \
    @telosnetwork/telosevm-js@0.1.1-18

WORKDIR /root

COPY ./scripts /root/scripts
COPY ./tests /root/tests

WORKDIR /root/tests
