# Home Assistant

## Hoje (funcional, via nuvem)
Para controle no HA **agora**, use o add-on MQTT (depende da nuvem Intelbras):
- **[rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net)** — original.
- **[wesleycp4/ha-elc6012net](https://github.com/wesleycp4/ha-elc6012net)** — fork
  com suporte ao firmware que responde o status em 164 bytes (sem checksum),
  RSSI com sinal e build local. Expõe: `alarm_control_panel`, `switch.choque`,
  `binary_sensor.zona_1..8`, `switch.bypass_zona_1..8`, `sensor.ultimo_evento`,
  `event.cerca_eletrica`, etc.

## Objetivo deste projeto (local, sem nuvem)
Substituir o relay da Intelbras por um **relay local** (`relay/elc_local_relay.py`):
a central conecta nele, e o HA recebe tudo por MQTT **sem sair da sua rede** —
controle, eventos e (no futuro) configuração. Status: protótipo; ver
[STATUS](STATUS.md). O modelo de entidades será o mesmo do add-on acima, para
migração transparente.
