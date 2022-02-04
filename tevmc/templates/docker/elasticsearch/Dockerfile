FROM docker.elastic.co/elasticsearch/elasticsearch:7.16.3
COPY --chown=elasticsearch:elasticsearch elasticsearch.yml /usr/share/elasticsearch/config/

RUN mkdir -p /var/log/elasticsearch
RUN chown -R elasticsearch:elasticsearch /var/log/elasticsearch
RUN mkdir -p /var/data/elasticsearch
RUN chown -R elasticsearch:elasticsearch /var/data/elasticsearch

EXPOSE $elasticsearch_port
