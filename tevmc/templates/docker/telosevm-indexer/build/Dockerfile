FROM node:16-bullseye

RUN npm i pm2 -g

RUN git clone https://github.com/telosnetwork/telosevm-es-indexer.git indexer --branch jesse_refactor

RUN rm -rdf /indexer/.git \
    /indexer/node_modules \
    /indexer/package-lock.json

RUN mkdir -p /indexer/build

WORKDIR /indexer

RUN npm i
RUN npx tsc
# CMD ["pm2-runtime", "start", "build/main.js"]
CMD ["node", "build/main.js"]

EXPOSE $broadcast_port
