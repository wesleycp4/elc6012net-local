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
a central conecta nele e passa a ser controlada 100% localmente. **O controle
(arme/desarme/choque/tudo) já está confirmado ao vivo** pelo painel web/stdin do
relay (ver [STATUS](STATUS.md)). Falta a ponte para o Home Assistant.

### Caminho para o HA local (próximo passo)
O relay já expõe `GET /status` (JSON) e `POST /cmd/<nome>`. Duas opções:

- **Stopgap sem mexer no relay:** integrações nativas do HA apontando pro relay —
  `rest_command` para os `POST /cmd/*`, sensor `rest` lendo `/status`, e
  `template`/`switch`/`binary_sensor` para choque, alarme e disparo.
- **Alvo (limpo):** adicionar **MQTT Discovery** ao relay (publica em mudança de
  estado, assina um tópico de comando → aciona o controle), espelhando as entidades
  do add-on de nuvem acima (`alarm_control_panel`, `switch.choque`,
  `binary_sensor.zona_1..8`, `switch.bypass_zona_1..8`, `event`) para migração
  transparente. A fazer no relay: disponibilidade/frescor (online + idade do
  status), zonas/bypass decodificados por bit, e publicação dos eventos `10 b2`.
