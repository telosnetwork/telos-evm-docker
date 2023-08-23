#!/bin/bash

set -e

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
  echo "Poetry is not installed. Installing now..."
  curl -sSL https://install.python-poetry.org | python -
else
  echo "Poetry is already installed."
fi

poetry install
