FROM alpine:latest
RUN apk add --no-cache logrotate dcron
COPY logrotate.conf /etc/logrotate.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]

