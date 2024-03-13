FROM docker.elastic.co/elasticsearch/elasticsearch:8.12.1

COPY elasticsearch.yml /usr/share/elasticsearch/config/

COPY entrypoint.sh /bin/entrypoint.sh

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
