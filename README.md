# telos-evm-docker
## Docker container for local EVM development and building automated tests

## Execution
`./run.sh` will destroy the container (if it exists), build, and then run the container.

The container will bind to the localhost's 8888 for http RPC and 8080 for state-history, you can run cleos and it will then default to the container