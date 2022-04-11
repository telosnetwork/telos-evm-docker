FROM docker.elastic.co/elasticsearch/elasticsearch:7.16.3

COPY elasticsearch.yml /usr/share/elasticsearch/config/

RUN mkdir -p /home/elasticsearch/data
RUN chown -R elasticsearch:elasticsearch /home/elasticsearch/data
RUN mkdir -p /home/elasticsearch/logs
RUN chown -R elasticsearch:elasticsearch /home/elasticsearch/logs

RUN printf "temporal" | ./bin/elasticsearch-keystore add -f -x "bootstrap.password"

EXPOSE $elasticsearch_port
