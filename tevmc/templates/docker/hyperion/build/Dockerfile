FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y \
        git \
        vim \
        less \
        curl \
        netcat \
        build-essential

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs && \
    npm install pm2 -g && \
    git clone https://github.com/eosrio/hyperion-history-api.git && \
    cd hyperion-history-api && \
    git checkout v3.3.5

WORKDIR /hyperion-history-api

COPY home/.ssh /root/.ssh
RUN chmod -R 600 "/root/.ssh/config"
RUN chmod -R 600 "/root/.ssh/evm_plugin"

RUN npm i
RUN npm i @fastify/autoload

RUN ./hpm install -r git@github.com:telosnetwork/hyperion-telos-evm-plugin.git telos-evm
RUN ./hpm enable telos-evm

RUN ./hpm install -r https://github.com/eosrio/hyperion-explorer-plugin explorer
RUN ./hpm enable explorer

RUN pm2 install pm2-logrotate
RUN pm2 set pm2-logrotate:max_size 10M
RUN pm2 set pm2-logrotate:retain 30
RUN pm2 set pm2-logrotate:compress true
RUN pm2 set pm2-logrotate:dateFormat YYYY-MM-DD_HH-mm-ss
RUN pm2 set pm2-logrotate:workerInterval 30
RUN pm2 set pm2-logrotate:rotateInterval 0 0 * * *
RUN pm2 set pm2-logrotate:rotateModule true

COPY connections.json connections.json
COPY ecosystem.config.js ecosystem.config.js

COPY scripts /root/scripts

EXPOSE $api_port
EXPOSE $ws_port
EXPOSE $rpc_port
EXPOSE $ws_router_port
