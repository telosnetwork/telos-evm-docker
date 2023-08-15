mkdir -p /home/elasticsearch/data /home/elasticsearch/logs

chown -R elasticsearch:elasticsearch /home/elasticsearch
echo "permissions setup done."

/bin/tini -- /usr/local/bin/docker-entrypoint.sh
