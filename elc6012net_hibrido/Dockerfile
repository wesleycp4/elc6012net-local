# O Supervisor passa só BUILD_ARCH; a imagem base é montada a partir dela.
ARG BUILD_ARCH=amd64
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base:3.23
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip tzdata \
    && pip3 install --no-cache-dir --break-system-packages "paho-mqtt>=2.1,<3"

# Código do relay baixado da branch experimental (modo híbrido).
# Um "Recompilar" no HA busca a versão mais nova da branch.
ARG BRANCH=experimental
ADD https://raw.githubusercontent.com/wesleycp4/elc6012net-local/${BRANCH}/relay/elc_local_relay.py /app/
ADD https://raw.githubusercontent.com/wesleycp4/elc6012net-local/${BRANCH}/relay/mqtt_bridge.py /app/

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
