FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get autoremove && \
    apt-get install -y \
        git \
        vim \
        less \
        curl \
        netcat \
        build-essential

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs && \
    npm install pm2 -g && \
    git clone https://github.com/guilledk/hyperion-history-api.git && \
    cd hyperion-history-api && \
    git checkout v3.3.5 

WORKDIR /hyperion-history-api

COPY home/.ssh /root/.ssh
RUN chmod -R 600 "/root/.ssh/config"
RUN chmod -R 600 "/root/.ssh/evm_plugin"

RUN npm install

RUN ./hpm install -b websocket -r git@github.com:telosnetwork/hyperion-telos-evm-plugin.git telos-evm
RUN ./hpm enable telos-evm

RUN ./hpm install -r https://github.com/eosrio/hyperion-explorer-plugin explorer
RUN ./hpm enable explorer

COPY connections.json connections.json
COPY ecosystem.config.js ecosystem.config.js

COPY scripts /root/scripts

EXPOSE $api_port
