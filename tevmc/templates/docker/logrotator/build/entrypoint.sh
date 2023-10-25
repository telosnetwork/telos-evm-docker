#!/bin/sh
echo '0 0 * * * /usr/sbin/logrotate /etc/logrotate.conf' > /etc/crontabs/root
crond -l 2 -f
