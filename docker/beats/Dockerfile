FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget \
        ca-certificates

# logging config
RUN wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.16.3-amd64.deb && \
    dpkg -i filebeat-7.16.3-amd64.deb

COPY filebeat.yml /etc/filebeat

RUN mkdir /root/logs/

CMD filebeat -e
