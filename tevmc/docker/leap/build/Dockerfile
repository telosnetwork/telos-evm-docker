from --platform=linux/amd64 ubuntu:22.04

env DEBIAN_FRONTEND=noninteractive

run apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        git \
        wget \
        zstd \
        binutils \
        ca-certificates

# install snapshots from latest evm deployments
workdir /
run wget http://storage.telos.net/test-resources/telos-mainnet-snapshot-evm-deploy.bin
run wget http://storage.telos.net/test-resources/telos-testnet-snapshot-evm-deploy.bin

# install nodeos
workdir /root
run wget https://github.com/telosnetwork/leap/releases/download/v4.0.4-1.0.2-rc2/leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb && \
    apt-get install -y -f ./leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb

# # install vanilla nodeos
# run wget https://github.com/AntelopeIO/leap/releases/download/v4.0.4/leap_4.0.4-ubuntu20.04_amd64.deb && \
#     ar x leap_4.0.4-ubuntu20.04_amd64.deb && \
#     tar xvf data.tar.gz && \
#     cp ./usr/bin/nodeos /usr/local/bin/nodeos-vanilla && \
#     rm -rdf usr data.tar.gz control.tar.gz debian-binary *.deb

# # install local deb
# copy ./leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb .
# run apt-get install -f -y ./leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb
