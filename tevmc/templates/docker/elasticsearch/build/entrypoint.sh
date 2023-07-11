chown -R elasticsearch:elasticsearch /home/elasticsearch
echo "permissions setup done."

/bin/tini -- /usr/local/bin/docker-entrypoint.sh
