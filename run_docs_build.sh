#!/bin/bash

if [ "$#" -ne 1 ] || ! [ -e "$1" ]; then
  echo 'Usage: $0 path_to_file'
  exit 1
fi

OUTPUT_PATH="$1"

echo "Writing docs to $OUTPUT_PATH..."

lazydocs \
    --output-path=$OUTPUT_PATH \
    --overview-file=overview.md \
    tevmc tevmc.tevmc

grep -rl '<img' $OUTPUT_PATH | xargs sed -i '/<img/d'
