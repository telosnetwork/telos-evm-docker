FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        git \
        wget \
        zstd \
        binutils \
        ca-certificates

# install snapshots from latest evm deployments
WORKDIR /

RUN wget https://telos-snapshots.s3.amazonaws.com/testnet/telos-testnet-20211020-blknum-136229794.tar.gz &&\
    tar xvf telos-testnet-20211020-blknum-136229794.tar.gz && \
    mv \
        snapshot-081eb3a22f5d3aeb348599b02f3afdd31adc36f278b0fbaba60441608015d58f.bin \
        snapshot-testnet-20211020-blknum-136229794.bin

RUN wget https://telos-snapshots.s3.amazonaws.com/mainnet/telos-mainet-20211026-blk-180635436.tar.gz && \
    tar xvf telos-mainet-20211026-blk-180635436.tar.gz && \
    mv \
        snapshot-0ac4472c3af648291761dad85c9090333474a733dd1852008e2d1d41b212a0fc.bin \
        snapshot-mainnet-20211026-blk-180635436.bin

WORKDIR /root

RUN wget https://github.com/AntelopeIO/leap/releases/download/v4.0.6/leap_4.0.6-ubuntu22.04_amd64.deb && \
    apt-get install -y -f ./leap_4.0.6-ubuntu22.04_amd64.deb

EXPOSE $nodeos_port
EXPOSE $nodeos_history_port

CMD ["/bin/bash", "-c", "while true; do sleep 3; done;"]

# COPY entrypoint.sh /opt/entrypoint.sh

# ENTRYPOINT ["/bin/bash", "/opt/entrypoint.sh"] 
