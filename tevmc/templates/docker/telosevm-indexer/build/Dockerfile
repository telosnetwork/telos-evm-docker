FROM node:lts-bullseye

RUN npm i pm2 -g

COPY telosevm-es-indexer/ /indexer

RUN mkdir -p /indexer/build

WORKDIR /indexer

RUN npm i
RUN npx tsc
# CMD ["pm2-runtime", "start", "build/main.js"]
CMD ["node", "build/main.js"]

EXPOSE $broadcast_port
