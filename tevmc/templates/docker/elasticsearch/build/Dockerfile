FROM docker.elastic.co/elasticsearch/elasticsearch:7.17.4

COPY elasticsearch.yml /usr/share/elasticsearch/config/

RUN mkdir -p /home/elasticsearch/data
RUN mkdir -p /home/elasticsearch/logs

RUN printf "temporal" | ./bin/elasticsearch-keystore add -f -x "bootstrap.password"

EXPOSE $elasticsearch_port

COPY entrypoint.sh /bin/entrypoint.sh

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
