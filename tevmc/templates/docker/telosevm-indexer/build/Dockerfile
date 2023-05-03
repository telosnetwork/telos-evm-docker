from node:18-bullseye

workdir /root

run git clone https://github.com/telosnetwork/telosevm-es-indexer.git indexer --branch default_conf

run rm -rdf indexer/.git indexer/yarn.lock

workdir /root/indexer

run yarn install
run npx tsc

env LOG_LEVEL debug

cmd ["node", "--expose-gc", "build/main.js"]

expose $broadcast_port
