#!/bin/bash
ENV_PATH="$(poetry env info --path)"
if [ -z "$ENV_PATH" ]; then
  echo "Failed to find the virtual environment path."
  return 1
fi
echo "Virtual environment path: $ENV_PATH"
source "$ENV_PATH/bin/activate"
echo "Virtual environment activated successfully."
