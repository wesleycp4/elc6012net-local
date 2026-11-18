# Home Assistant

O relay publica a central no Home Assistant por **MQTT Discovery**: as entidades
aparecem sozinhas, o estado é atualizado a cada leitura e os comandos voltam pelo
mesmo broker. Tudo local — não depende de internet.

Instalação e o caminho até a central conectar: [instalacao.md](instalacao.md).

## Apps

| App | Uso | Estado |
|---|---|---|
| **ELC 6012 NET Local** | relay local, sem nuvem | estável |
| **ELC 6012 NET Híbrido** | relay que também repassa para a nuvem Intelbras, tentando manter o app oficial | experimental |

Os dois escutam na porta 9009: rode um por vez. As credenciais do MQTT vêm do App
Mosquitto automaticamente.

### Opções

| Opção | App | Padrão | Descrição |
|---|---|---|---|
| `poll` | Local | `5` | intervalo de leitura do status, em segundos |
| `node` | ambos | `elc6012_local` / `elc6012_hibrido` | id do dispositivo no HA (prefixo dos tópicos) |
| `name` | ambos | `ELC 6012 NET (local)` / `(híbrido)` | nome do dispositivo |
| `upstream` | Híbrido | `52.67.212.35:9009` | servidor da nuvem Intelbras |
| `inject_session` | Híbrido | `2` | índice da sessão usada pelos comandos locais |

A hora enviada à central usa o fuso do Home Assistant.

## Entidades

Com `name: ELC 6012 NET (local)`, os ids ficam com o prefixo `elc_6012_net_local_`:

| Entidade | Tipo | Comando |
|---|---|---|
| `alarm_control_panel.…_alarme` | alarme (partição 1) | armar / desarmar; estado `triggered` no disparo |
| `switch.…_cerca` | choque da cerca (partição 2) | liga / desliga |
| `binary_sensor.…_disparo` | alguma zona disparada | — |
| `binary_sensor.…_zona_1` … `_zona_8` | zona aberta | — |

A disponibilidade segue a conexão da central: com a central desconectada do relay, as
entidades ficam indisponíveis. A queda é detectada por erro de conexão ou por 60 s sem
nenhum dado da central. Comandos enviados nesse intervalo são descartados.

Para ser avisado de uma queda, crie uma automação com gatilho de estado
`unavailable` por alguns minutos na entidade do alarme.

As zonas seguem a numeração da central. Renomeie as entidades com os nomes que você
usa (os nomes cadastrados na central ficam no bloco de configuração `00 00`).

> **Zonas com a central desarmada.** A atualização de "zona aberta" com a central
> desarmada é intermitente — o mesmo acontece no app oficial. Com o alarme armado, a
> abertura gera disparo imediato. Não use as zonas desarmadas como sensor de porta
> confiável.

## Tópicos MQTT

Base `elc6012/<node>`:

| Tópico | Conteúdo |
|---|---|
| `…/availability` | `online` / `offline` |
| `…/state` | JSON com `choque`, `alarme`, `disparo`, `zona1`…`zona8` |
| `…/alarme/set` | `ARM_AWAY` / `DISARM` |
| `…/cerca/set` | `ON` / `OFF` |

## Dashboard de exemplo

Painel em *sections*, com o choque protegido por "segurar e confirmar":

```yaml
type: sections
title: Cerca elétrica
path: cerca
icon: mdi:fence-electric
max_columns: 3
sections:
  - type: grid
    cards:
      - type: heading
        heading: Cerca elétrica
        icon: mdi:fence-electric
      - type: tile
        entity: alarm_control_panel.elc_6012_net_local_alarme
        name: Alarme
        features:
          - type: alarm-modes
            modes: [armed_away, disarmed]
        grid_options: {columns: full}
      - type: tile
        entity: switch.elc_6012_net_local_cerca
        name: Choque — segure para alterar
        icon: mdi:flash
        color: red
        tap_action: {action: more-info}
        hold_action:
          action: perform-action
          perform_action: switch.toggle
          target: {entity_id: switch.elc_6012_net_local_cerca}
          confirmation: {text: Confirmar alteração do choque da cerca?}
        grid_options: {columns: full}
      - type: tile
        entity: binary_sensor.elc_6012_net_local_disparo
        name: Disparo
        color: red
  - type: grid
    cards:
      - type: heading
        heading: Portas e janelas
        icon: mdi:door
      - type: tile
        entity: binary_sensor.elc_6012_net_local_zona_1
        grid_options: {columns: 6}
      # … zona_2 a zona_8
```

## Sem MQTT

O relay avulso tem um painel web (`--web <porta>`, só em `127.0.0.1`) com `GET /status`
e `POST /cmd/<comando>`. Dá para usar com `rest_command` e um sensor `rest`, mas sem
descoberta automática e com polling — o caminho recomendado é o MQTT.

## Ainda não exposto

O relay já fala os comandos abaixo, mas eles ainda não viraram entidades:

- bypass de zona (`switch` por zona);
- eventos Contact-ID (`event` / último evento), incluindo rede elétrica e bateria;
- PGM e pânico.
