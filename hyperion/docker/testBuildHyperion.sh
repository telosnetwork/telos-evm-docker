#!/bin/bash

cp -a ./scripts ./hyperion/scripts
cd ./hyperion
docker build -t telos.net/hyperion:0.1.0 .
cd -
rm -rf ./hyperion/scripts
