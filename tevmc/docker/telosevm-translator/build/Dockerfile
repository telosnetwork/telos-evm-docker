from node:18-bullseye

workdir /root

run git clone \
    https://github.com/telosnetwork/telosevm-translator.git \
    indexer \
    -b simple_2_0

workdir /root/indexer

run npm run build

cmd ["/bin/bash", "-c", "node build/main.js --config=/root/indexer/config/config.json >> /logs/telosevm-translator.log 2>&1"]
