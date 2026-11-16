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
relay (ver [STATUS](STATUS.md)). A ponte local para o Home Assistant via MQTT
(`relay/mqtt_bridge.py`) foi **validada ao vivo** em 16/11/2026: entidades criadas,
arme/desarme e cerca comandados pelo HA.

### Integração local via MQTT Discovery (pronta)
O relay traz uma ponte MQTT (`relay/mqtt_bridge.py`) que cria as entidades no HA
automaticamente (MQTT Discovery), publica o estado quando a central muda e recebe
os comandos — **tudo local, sem nuvem e sem internet**.

Entidades criadas: `switch.cerca` (choque), `alarm_control_panel.alarme`
(armar/desarmar, estado `disparo`→`triggered`), `binary_sensor.disparo` e
`binary_sensor.zona_1..8`.

**Jeito mais fácil — App do HA (HA OS/Supervised):** em *Configurações → Apps →
Loja → ⋮ → Repositórios*, adicione `https://github.com/wesleycp4/elc6012net-local`
e instale um dos dois (só um por vez, ambos usam a porta 9009):

- **ELC 6012 NET Local** — modo validado, sem nuvem (código da `main`).
- **ELC 6012 NET Híbrido (experimental)** — tenta manter a nuvem/app Intelbras e
  injetar comandos locais (código da `experimental`; no teste ao vivo o app oficial
  não entrou).

As credenciais do Mosquitto vêm sozinhas. Cada App tem a aba *Documentação* com o
redirecionamento de DNS necessário (`amt8000.intelbras.com.br → IP do HA`) —
obrigatório nos dois Apps; ver [redirecionamento.md](redirecionamento.md).

**Passo a passo manual (fora do HA OS):**
1. Tenha um broker MQTT na rede — no HA OS, instale o add-on **Mosquitto broker** e
   a integração **MQTT** (a descoberta já vem ligada).
2. No gateway onde roda o relay: `pip install paho-mqtt`.
3. Rode o relay apontando pro broker:
   ```bash
   python3 relay/elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 \
       --mqtt SEU_BROKER:1883 --mqtt-user USUARIO --mqtt-pass SENHA
   ```
4. As entidades aparecem sozinhas no HA (dispositivo "Intelbras ELC 6012 NET").
   Se a internet cair, continua tudo funcionando — a central fala com o relay e o
   relay com o HA, tudo na sua LAN.

A disponibilidade segue a central (online/offline via LWT). As zonas `zona_1..8`
seguem a numeração da central (bits confirmados ao vivo); os nomes de cada zona
estão no bloco de config `00 00` — renomeie as entidades no HA conforme eles.

### Alternativa sem MQTT (stopgap)
Sem broker, dá pra usar as integrações nativas do HA apontando pro relay:
`rest_command` para os `POST /cmd/*` e um sensor `rest` lendo `GET /status`
(porém com polling e sem descoberta automática).

### A evoluir no relay (contribuições)
Publicar os eventos `10 b2` (Contact-ID, já decodificados em PROTOCOL §4.7) como
entidade `event`, `switch.bypass_zona_1..8` e nomes das zonas lidos da central.
