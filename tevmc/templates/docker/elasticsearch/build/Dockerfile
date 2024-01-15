FROM docker.elastic.co/elasticsearch/elasticsearch:8.11.3

COPY elasticsearch.yml /usr/share/elasticsearch/config/

EXPOSE $elasticsearch_port

COPY entrypoint.sh /bin/entrypoint.sh

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
