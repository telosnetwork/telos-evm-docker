FROM ubuntu:20.04

RUN apt-get update && apt-get upgrade -y && apt-get autoremove && apt-get install -y build-essential git curl netcat

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs && npm install pm2 -g && git clone https://github.com/eosrio/hyperion-history-api.git && cd hyperion-history-api && git checkout v3.3.5

COPY ./config/connections.json /hyperion-history-api/connections.json
COPY ./config/ecosystem.config.js /hyperion-history-api/ecosystem.config.js
COPY ./config/chains/ /hyperion-history-api/chains/
COPY ./home /home/hyperion/
COPY ./scripts/ /home/hyperion/scripts/

RUN useradd -m -s /bin/bash hyperion && chown -R hyperion:hyperion /hyperion-history-api && chown -R hyperion:hyperion /home/hyperion
RUN chmod -R 600 "/home/hyperion/.ssh/config"
RUN chmod -R 600 "/home/hyperion/.ssh/evm_plugin"
USER hyperion
WORKDIR /hyperion-history-api

RUN npm install

RUN ./hpm install -b main -r git@github.com:telosnetwork/hyperion-telos-evm-plugin.git telos-evm
RUN ./hpm enable telos-evm

RUN ./hpm install -r https://github.com/eosrio/hyperion-explorer-plugin explorer
RUN ./hpm enable explorer

EXPOSE 7000
