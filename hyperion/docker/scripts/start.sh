#!/bin/bash

usage() {
  exitcode="$1"

  echo "Usage:$cmdname --chain string [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  -s, --snapshot string  file path of chain snapshot"

  exit "$exitcode"
}

wait_for_container() {
  container_ip=`docker inspect --format='{{json .NetworkSettings.Networks.docker_hyperion.IPAddress}}' $1`

  ./scripts/wait-for.sh "${container_ip//\"}:$2"
}

chain="telos-testnet"

while [ $# -gt 0 ]
do
  key="$1"

  case $key in
    --chain)
    chain="$2"
    shift
    shift
    ;;
    -s|--snapshot)
    snapshot="$2"
    shift
    shift
    ;;
    -h|--help)
    usage 0
    ;;
    *)
    echo "Unknown argument: $1"
    usage 1
    ;;
  esac
done

if [ "$chain" = "" ]; then
  echo "Error: you need to provide chain identificator"
  usage 2
fi

chmod -R 777 ./elasticsearch
#chmod -R 777 ./rabbitmq
chmod -R 777 ./hyperion

cp -a ./scripts ./hyperion/scripts
cp -a ./hyperion-home ./hyperion/hyperion-home
cd ./hyperion
docker build -t telos.net/hyperion:0.1.0 .
cd -
rm -rf ./hyperion/scripts
rm -rf ./hyperion/hyperion-home

created="$(docker container ls -q --all)"

#if [ "$created" = "" ]
#then
  # Create docker containers
  SCRIPT=true SNAPSHOT=$snapshot docker-compose up --no-start
#fi

# Starting redis container
docker-compose start redis

# Starting rabbitmq container
docker-compose start rabbitmq

# Starting elasticsearch container
# wait_for_container rabbitmq 5672
# on mac you cannot access the container IP, use the one exposed on the host
./scripts/wait-for.sh "localhost:15672"

retry_count=0
until [ $(curl --silent -u username:password -X GET http://127.0.0.1:15672/api/definitions | jq -e '.vhosts | length') -ge 1 ]; do
  if [ $retry_count -ge 60 ]; then
    echo "Failure - exceeded wait time for rabbit to become healthy"
    exit 1
  fi
  echo "waiting for rabbit to come online..."
  sleep 3
  ((retry_count++))
done


if [ $? -ne 0 ]
then
  echo "failed to wait for rabbitmq"
  exit 1
fi

docker-compose start elasticsearch

# Starting kibana container
# wait_for_container elasticsearch 9200
./scripts/wait-for.sh "localhost:9200"

if [ $? -ne 0 ]
then
  echo "failed to wait for elasticsearch"
  exit 1
fi

retry_count=0
until curl -u elastic:password -s -X GET "http://localhost:9200/_cat/health" | awk '{ print $4 }' | egrep -q 'green|yellow'; do
  if [ $retry_count -ge 60 ]; then
    echo "Failure - exceeded wait time for elastic to become healthy"
    exit 1
  fi
  echo "waiting for elastic to come online..."
  sleep 3
  ((retry_count++))
done

docker-compose start kibana

# Starting eosio-node container
#docker-compose start eosio-node

# Starting hyperion containers
#wait_for_container eosio_nodeos 8888
./scripts/wait-for.sh "localhost:8888"

if [ $? -ne 0 ]
then
  echo "failed to wait for eosio-node"
  exit 1
fi

if [ "$snapshot" != "" ]
then
  file="$(docker inspect --format='{{.LogPath}}' eosio-node)"
  line="$(sudo grep -h 'Placing initial state in block' $file)"

  if [ "$line" != "" ]
  then
    block_num="$(echo $line | sed 's/.*block //' | sed 's/n.*//g' | sed 's/[^0-9]*//g')"
    sed -i "s/\"start_on\": 1/\"start_on\": $block_num/" hyperion/config/chains/$chain.config.json
  fi
fi

docker-compose start hyperion-indexer
docker-compose start hyperion-api
