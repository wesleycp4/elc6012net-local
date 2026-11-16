#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

if ! bashio::services.available "mqtt"; then
    bashio::exit.nok "Broker MQTT não encontrado — instale/inicie o App Mosquitto."
fi

export MQTT_PASSWORD
MQTT_PASSWORD="$(bashio::services mqtt 'password')"

bashio::log.warning "MODO HÍBRIDO (EXPERIMENTAL): repassando para a nuvem $(bashio::config 'upstream')"
exec python3 -u /app/elc_local_relay.py \
    --listen 0.0.0.0:9009 --daemon \
    --upstream "$(bashio::config 'upstream')" \
    --inject-session "$(bashio::config 'inject_session')" \
    --mqtt "$(bashio::services mqtt 'host'):$(bashio::services mqtt 'port')" \
    --mqtt-user "$(bashio::services mqtt 'username')" \
    --mqtt-node "$(bashio::config 'node')" \
    --mqtt-name "$(bashio::config 'name')"
