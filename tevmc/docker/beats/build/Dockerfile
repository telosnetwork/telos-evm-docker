FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget \
        ca-certificates

# logging config
RUN wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.15.1-amd64.deb && \
    dpkg -i filebeat-7.15.1-amd64.deb

RUN mkdir /root/logs/
RUN mkdir /root/config

CMD ["/bin/bash", "-c", "while true; do sleep 3; done;"]
