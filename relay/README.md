# Relay local

`elc_local_relay.py` faz o papel do servidor da nuvem: a central conecta nele e passa
a ser controlada localmente. `mqtt_bridge.py` publica a central no Home Assistant.

No Home Assistant, prefira o App (ver [instalação](../docs/instalacao.md)). Este
documento cobre o uso avulso.

## Requisitos

- Python 3.11+
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
| `--upstream HOST[:PORTA]` | desligado | modo híbrido (ver abaixo) |
| `--inject-session N` | `2` | sessão dos comandos locais no modo híbrido |
| `--session-hex HEX` | payload padrão | abertura de sessão alternativa (diagnóstico) |

`--code` e `--keepalive` existem só por compatibilidade e são ignorados. Ao receber
`SIGTERM` (parada do serviço/App), o relay encerra a sessão de controle (`f0 f1`) antes
de sair, para não deixá-la presa na central.

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

Cada linha começa com o horário. O status é impresso só quando muda.

| Mensagem | Significado |
|---|---|
| `== central conectou de …` / `[SESSAO] aberta` | central conectada e sessão de controle liberada |
| `[SESSAO] central respondeu código 0x01` | sessão anterior presa na central; o relay encerra (`f0 f1`) e reabre sozinho |
| `[SESSAO] reaberta com controle liberado` | a liberação funcionou |
| `[SESSAO] continua sem controle…` | não liberou: desligue e religue a central |
| `[OK] … confirmado pelo status` | arme/desarme/choque aplicado |
| `[=] …: já está nesse estado` | comando não enviado, a central já estava no estado pedido |
| `[RECUSADO] … code 0xNN (frame)` | recusa da central (`0x21` = sem sessão de controle ou função não permitida). Arme/desarme/choque são conferidos pelo status e reenviados até 2×; os demais comandos são reenviados até 2× reabrindo a sessão |
| `[!] central desconectou (motivo)` | erro de conexão ou 60 s sem dados; o HA marca as entidades como indisponíveis até a central reconectar |

## Modo híbrido (não validado)

Com `--upstream <host:porta>`, o relay repassa o tráfego da central para a nuvem
Intelbras e injeta os comandos locais numa sessão própria (`--inject-session`, padrão
`2`). Os frames dessa sessão não são repassados à nuvem. Se a internet cair, o
controle local continua e o túnel é refeito quando ela volta.

```bash
python3 elc_local_relay.py --listen 0.0.0.0:9009 --upstream 52.67.212.35:9009 \
    --inject-session 2 --mqtt <broker>:1883
```

Use o IP da nuvem em `--upstream`, não o nome, para não cair no próprio
redirecionamento. O app oficial não reconectou nos testes — ver
[STATUS](../docs/STATUS.md).
