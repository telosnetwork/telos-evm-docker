from node:18-bullseye

workdir /root

run git clone https://github.com/telosnetwork/telosevm-translator.git indexer -b ws_hotfix

run rm -rdf indexer/.git

workdir /root/indexer

run yarn install
run npx tsc

env LOG_LEVEL debug

cmd ["node", "--expose-gc", "build/main.js"]

expose $broadcast_port
