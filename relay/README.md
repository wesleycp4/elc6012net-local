# Relay local

`elc_local_relay.py` faz o papel do servidor da nuvem: a central conecta nele e passa
a ser controlada localmente. `mqtt_bridge.py` publica a central no Home Assistant.

No Home Assistant, prefira o App (ver [instalação](../docs/instalacao.md)). Este
documento cobre o uso avulso.

## Requisitos

- Python 3.9+
- `paho-mqtt` — só para a integração MQTT (`pip install -r requirements.txt`)
- A central redirecionada para esta máquina ([instalação, etapa 1](../docs/instalacao.md#etapa-1--fazer-a-central-chegar-no-relay))

## Uso

```bash
python3 elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 --tz America/Sao_Paulo --web 8088
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--listen HOST:PORTA` | `0.0.0.0:9009` | endereço onde a central conecta |
| `--poll N` | `15` | intervalo de leitura do status, em segundos |
| `--tz FUSO` | env `TZ` | fuso da hora enviada à central (ex.: `America/Sao_Paulo`) |
| `--web PORTA` | desligado | painel web em `127.0.0.1:PORTA` |
| `--mqtt HOST[:PORTA]` | desligado | broker MQTT para o Home Assistant |
| `--mqtt-user` | — | usuário do broker (senha em `MQTT_PASSWORD` ou `--mqtt-pass`) |
| `--mqtt-node` | `elc6012net` | id do dispositivo no HA |
| `--mqtt-name` | `Intelbras ELC 6012 NET` | nome do dispositivo no HA |
| `--daemon` | — | sem terminal interativo (serviço) |

`--code` e `--keepalive` existem só por compatibilidade e são ignorados.

## Comandos

Pelo terminal (stdin):

| Comando | Ação |
|---|---|
| `arm` / `disarm` | arma / desarma o alarme |
| `shockon` / `shockoff` | liga / desliga o choque |
| `allon` / `alloff` | alarme e choque juntos |
| `status` | lê o status |
| `bypass <8 dígitos>` | anula zonas (`00100000` anula a zona 3) |
| `panic [0-1]` | pânico silencioso (`0`) ou audível (`1`) |
| `sirenoff` | silencia a sirene |
| `pgm <1\|2> <on\|off>` | aciona uma PGM (só em modo "acesso via app") |
| `events` | lê o histórico de eventos |
| `raw <hex>` | envia um payload arbitrário |
| `quit` | encerra |

O painel web (`--web`) oferece arme/desarme e choque com status ao vivo; ele não pede
confirmação e só escuta em `127.0.0.1`.

## Log

O status é impresso só quando muda. Recusas da central aparecem como
`[RECUSADO] code 0xNN` (`0x21` = função não permitida); o relay reabre a sessão e
reenvia até duas vezes. Para arme/desarme/choque, o resultado é conferido no status
(`[OK] … confirmado pelo status`).

## Modo híbrido (experimental, branch `experimental`)

Com `--upstream <host:porta>`, o relay repassa o tráfego da central para a nuvem
Intelbras e injeta os comandos locais numa sessão própria (`--inject-session`).
O app oficial não reconectou nos testes — ver [STATUS](../docs/STATUS.md).
