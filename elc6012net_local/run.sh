#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

if ! bashio::services.available "mqtt"; then
    bashio::exit.nok "Broker MQTT não encontrado — instale/inicie o App Mosquitto."
fi

# Senha do broker por variável de ambiente (não aparece no ps).
export MQTT_PASSWORD
MQTT_PASSWORD="$(bashio::services mqtt 'password')"

bashio::log.info "Relay local ELC 6012 NET (sem nuvem) escutando na porta 9009"
exec python3 -u /app/elc_local_relay.py \
    --listen 0.0.0.0:9009 --daemon \
    --poll "$(bashio::config 'poll')" \
    --mqtt "$(bashio::services mqtt 'host'):$(bashio::services mqtt 'port')" \
    --mqtt-user "$(bashio::services mqtt 'username')" \
    --mqtt-node "$(bashio::config 'node')" \
    --mqtt-name "$(bashio::config 'name')"
