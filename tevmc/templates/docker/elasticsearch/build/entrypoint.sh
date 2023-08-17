mkdir -p /home/elasticsearch/data /home/elasticsearch/logs

chown -R elasticsearch:elasticsearch /home/elasticsearch
echo "permissions setup done."

su elasticsearch -c '/bin/tini -- /usr/local/bin/docker-entrypoint.sh'
