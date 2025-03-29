#!/bin/sh

envsubst < /etc/traefik/traefik.template.yml > /etc/traefik/traefik.yml
exec traefik --configFile=/etc/traefik/traefik.yml