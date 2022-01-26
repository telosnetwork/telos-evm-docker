#!/bin/sh

set -e

tevmc build --headless
tevmc up
tevmc wait-init

printf '\n\n\nTEVM up, run `tevmc down` to stop.\n\n\n'
