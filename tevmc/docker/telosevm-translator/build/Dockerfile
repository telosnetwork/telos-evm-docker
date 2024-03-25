from node:18-bullseye

workdir /root

run git clone \
    https://github.com/telosnetwork/telosevm-translator.git \
    indexer \
    -b index_config_fix

workdir /root/indexer

run npm run build

env LOG_LEVEL debug

cmd ["/bin/bash", "-c", "npm run start >> /logs/telosevm-translator.log 2>&1"]
