#!/bin/bash

_term() {
  kill -TERM "$child" 2>/dev/null
  pm2 stop "$app_name"
}

trap _term SIGTERM

echo $1

pm2 start --only $1 --update-env
pm2 logs --raw &

app_name=$1

child=$!
wait "$child"
