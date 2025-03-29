FROM alpine:3.19

RUN apk add --no-cache traefik gettext

COPY entrypoint.sh /entrypoint.sh
COPY traefik.template.yml /etc/traefik/traefik.template.yml

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]