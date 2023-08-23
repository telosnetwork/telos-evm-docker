#!/bin/bash

set -e

# Default installation location
INSTALL_LOCATION="/usr/local"

# If a parameter is passed, use it as the installation location
if [ "$#" -eq 1 ]; then
  INSTALL_LOCATION="$1"
fi

echo "Installing Poetry in $INSTALL_LOCATION..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
  echo "Poetry is not installed. Installing now..."
  export POETRY_HOME="$INSTALL_LOCATION"
  curl -sSL https://install.python-poetry.org | python3 -
else
  echo "Poetry is already installed."
fi

poetry install
