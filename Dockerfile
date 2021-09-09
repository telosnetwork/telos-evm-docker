FROM ubuntu:18.04

WORKDIR /opt/eosio/bin/

RUN apt-get update && apt-get install -y wget sudo curl git jq

RUN curl -sL https://deb.nodesource.com/setup_16.x | sudo bash - && \
apt-get install -yq nodejs build-essential

RUN wget https://github.com/EOSIO/eosio.cdt/releases/download/v1.6.3/eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb
RUN apt-get update && sudo apt install -y ./eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb
RUN wget https://github.com/EOSIO/eos/releases/download/v2.1.0/eosio_2.1.0-1-ubuntu-18.04_amd64.deb
RUN sudo apt install -y ./eosio_2.1.0-1-ubuntu-18.04_amd64.deb
RUN npm install eos-evm-js node-fetch@"<3.0.0" @telosnetwork/telosevm-js@0.1.1-18

COPY ./scripts/config.ini /mnt/dev/config/config.ini
COPY ./scripts/keosd_config.ini /root/eosio-wallet/config.ini
COPY ./scripts /opt/eosio/bin/scripts
COPY ./contracts /opt/eosio/bin/contracts
