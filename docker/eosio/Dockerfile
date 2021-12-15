FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget \
        libtinfo5 \
        ca-certificates

# install system contracts
COPY contracts /opt/eosio/bin/contracts

WORKDIR /root

# ubuntu 18.04 dependency 
RUN wget http://security.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3.2_amd64.deb && \
    apt-get install -y ./libicu60_60.2-3ubuntu3.2_amd64.deb

# install eosio tools
RUN wget https://github.com/EOSIO/eos/releases/download/v2.0.13/eosio_2.0.13-1-ubuntu-18.04_amd64.deb && \
    apt-get install -y ./eosio_2.0.13-1-ubuntu-18.04_amd64.deb

# cleanup root dir of .deb files
RUN rm -rf *.deb

# final configuration
COPY config.ini ./config.ini
COPY genesis.json ./genesis.json
EXPOSE 8888
