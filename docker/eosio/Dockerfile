FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget \
        make \
        cmake \
        libtinfo5 \
        build-essential \
        ca-certificates

# ubuntu 18.04 dependency 
RUN wget http://security.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3.2_amd64.deb && \
    apt-get install -y ./libicu60_60.2-3ubuntu3.2_amd64.deb

# get cdt 1.6.3
RUN wget https://github.com/EOSIO/eosio.cdt/releases/download/v1.6.3/eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb

# build & install telos system contracts
COPY telos.contracts /usr/opt/telos.contracts
WORKDIR /usr/opt/telos.contracts

# remove testing target from build
RUN head -n -10 CMakeLists.txt > .tmp_cmake && \
    mv .tmp_cmake CMakeLists.txt 

RUN cmake .
RUN make -j$(nproc --all)

# cleanup contracts directory
WORKDIR /usr/opt/telos.contracts/contracts
RUN rm -rdf icons CMakeFiles

# upgrade to cdt 1.7.0
WORKDIR /root
RUN wget https://github.com/EOSIO/eosio.cdt/releases/download/v1.7.0/eosio.cdt_1.7.0-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio.cdt_1.7.0-1-ubuntu-18.04_amd64.deb

# build & install telos.evm contract
COPY telos.evm /usr/opt/telos.evm
WORKDIR /usr/opt/telos.evm
RUN cmake .
RUN make -j$(nproc --all)
WORKDIR /usr/opt
RUN mv telos.evm telos.contracts/contracts/eosio.evm

WORKDIR /root

# install eosio tools
RUN wget https://github.com/EOSIO/eos/releases/download/v2.0.13/eosio_2.0.13-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio_2.0.13-1-ubuntu-18.04_amd64.deb

# cleanup root dir of .deb files
RUN rm -rf *.deb

# final configuration
COPY config.ini ./config.ini
COPY genesis.json ./genesis.json
EXPOSE 8888
