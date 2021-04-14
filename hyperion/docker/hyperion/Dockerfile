FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade -y && apt-get autoremove && apt-get install -y build-essential git curl netcat

RUN curl -sL https://deb.nodesource.com/setup_15.x | bash -
RUN apt-get install -y nodejs && npm install pm2 -g && git clone https://github.com/eosrio/hyperion-history-api.git && cd hyperion-history-api && git checkout dev-3.3

COPY ./config/connections.json /hyperion-history-api/connections.json
COPY ./config/ecosystem.config.js /hyperion-history-api/ecosystem.config.js
COPY ./config/chains/ /hyperion-history-api/chains/
COPY ./scripts/ /home/hyperion/scripts/

RUN useradd -m -s /bin/bash hyperion && chown -R hyperion:hyperion /hyperion-history-api
RUN chown -R hyperion:hyperion "/home/hyperion"
USER hyperion
WORKDIR /hyperion-history-api

RUN npm install

COPY ./config/plugins/ /hyperion-history-api/plugins/
RUN cd plugins/repos/explorer && npm install
RUN cd plugins/repos/explorer && npm run build
RUN cd plugins/repos/telos-evm && npm install && npm run build

EXPOSE 7001
