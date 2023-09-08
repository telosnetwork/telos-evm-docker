FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y git curl gnupg

RUN curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | tee /usr/share/keyrings/yarnkey.gpg >/dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -

RUN apt-get update && apt-get install -y yarn nodejs

RUN git clone https://github.com/telosnetwork/telos-evm-rpc.git

WORKDIR /telos-evm-rpc

RUN yarn

RUN npx tsc

COPY config.json config.json

CMD ["/bin/bash", "-c", "node dist/main.js >> /logs/telos-evm-rpc.log 2>&1"]

EXPOSE $api_port
EXPOSE $ws_port
