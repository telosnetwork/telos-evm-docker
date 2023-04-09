from node:16-bullseye

run npm i pm2 -g

workdir /root

run git clone git@github.com:telosnetwork/telosevm-es-indexer.git indexer --branch default_conf

run rm -rdf indexer/.git

workdir /root/indexer

run npm install -g npm@9.1.1
run yarn install
run npx tsc

run npm i why-is-node-running -g

env LOG_LEVEL debug

cmd ["why-is-node-running", "build/main.js"] 

expose $broadcast_port
