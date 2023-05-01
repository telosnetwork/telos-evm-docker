FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y gcc g++ git curl make gnupg

RUN curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | tee /usr/share/keyrings/yarnkey.gpg >/dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -

RUN apt-get update && apt-get install -y yarn nodejs

RUN npm install pm2 -g && \
    git clone https://github.com/eosrio/hyperion-history-api.git && \
    cd hyperion-history-api && \
    git checkout 4035de3dac18ec6d7f0e3dfa348e3db8bd7471f4

WORKDIR /hyperion-history-api

RUN npm i
# RUN npm i @fastify/autoload

RUN ./hpm install -r https://github.com/telosnetwork/hyperion-telos-evm-plugin.git -b evm_upgrade telos-evm
RUN ./hpm enable telos-evm

RUN ./hpm install -r https://github.com/eosrio/hyperion-explorer-plugin explorer
RUN ./hpm enable explorer

RUN pm2 install pm2-logrotate
RUN pm2 set pm2-logrotate:max_size 10M
RUN pm2 set pm2-logrotate:retain 3
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
