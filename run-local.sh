#!/bin/bash

set -e

tevmc clean
tevmc pull --headless

tevmc config --index-only-evm

tevmc build --headless
tevmc up --loglevel=info
tevmc wait-init

printf '\n\n\nTEVM Local testnet up, run `tevmc down` to stop.\n\n\n'
