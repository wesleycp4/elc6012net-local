# elc6012net-local

**Controle 100% local — sem nuvem — do eletrificador Intelbras ELC 6012 NET**,
mais a engenharia reversa do protocolo que viabiliza isso.

> ⚠️ Projeto independente, sem vínculo com a Intelbras. O protocolo foi obtido por
> engenharia reversa **do próprio equipamento** (captura de rede, texto claro), para
> fins de interoperabilidade. Controla uma cerca elétrica real — **use por sua conta
> e risco**. Enquanto a central fala com um relay local, ela não usa a nuvem
> Intelbras (sem as notificações da nuvem deles).

## Por quê

O ELC 6012 NET depende da nuvem Intelbras para tudo (status, arme/desarme, choque,
bypass, eventos) — o app "cai", exige internet e não oferece controle local. Mas o
protocolo é **TCP em texto claro, sem TLS e sem autenticação do servidor**: a
central aceita qualquer relay. Então dá para pôr a central para conectar num
**relay local** e ter controle total dentro de casa, com integração ao Home
Assistant, sem nuvem nenhuma.

## Como funciona

```
              redirecionamento na rede (DNS ou DNAT)
  ┌──────────┐   amt8000.intelbras.com.br → relay    ┌──────────────┐
  │ Central  │ ───────────────  TCP 9009  ─────────▶ │  Relay local │
  │ ELC 6012 │ ◀───── status / eventos / comandos ── │ (seu PC / HA)│
  └──────────┘                                        └──────┬───────┘
                                                             │ MQTT Discovery
                                                      ┌──────▼───────┐
                                                      │Home Assistant│
                                                      └──────────────┘
```

A central abre uma conexão TCP de saída procurando o servidor da nuvem; o
redirecionamento faz essa conexão cair no **relay local**, que fala o mesmo
protocolo (sem TLS, sem autenticação do servidor) e expõe tudo no Home Assistant.

**Modo híbrido** (experimental): o relay também repassa para a nuvem Intelbras
(central ⇄ relay ⇄ nuvem) para manter o app oficial, injetando os comandos locais
numa sessão própria — ver [docs/STATUS.md](docs/STATUS.md).

## ⚠️ Requisito: redirecionar a central

A central tem o servidor da nuvem **fixo no firmware** (`amt8000.intelbras.com.br`,
porta 9009) e não há configuração para trocá-lo. Para usar qualquer modo local —
inclusive o **Híbrido** — você precisa fazer esse nome apontar para o relay na sua
rede: DNS local no roteador, AdGuard Home/Pi-hole, uma rede só para a central ou
DNAT. **Sem controle do DNS/rede, o modo local não funciona** (resta a integração
via nuvem). Opções, como testar e gargalos:
**[docs/redirecionamento.md](docs/redirecionamento.md)**.

## Estado atual

**✅ Validado ao vivo (sem nuvem):**
- **Controle** — arme/desarme, choque e "tudo ligado/desligado", confirmado
  fisicamente pelo painel web e pelo Home Assistant.
- **Monitoração** — status de 164 bytes (choque, alarme, zonas, disparo, bypass,
  relógio, sinal), eventos Contact-ID e bits de zona 1–8.
- **Relay local** (`relay/elc_local_relay.py`) — enquadramento com re-sincronização,
  sessão de controle, confirmação de comando pelo status, painel web.
- **Home Assistant** via MQTT Discovery (`relay/mqtt_bridge.py`), e os dois **Apps do
  HA** (Local validado; Híbrido experimental) — ver [docs/homeassistant.md](docs/homeassistant.md).

**✅ Mapeado por captura** (protocolo completo): controle, eventos e configuração
(zonas, nome, PGMs, usuários, Wi-Fi) — ver [PROTOCOL.md](PROTOCOL.md).

**🟡 / ⬜ Pendente (não testado por nós):** modo híbrido (túnel funciona, mas o app
oficial não reconectou no teste), gravação de config pelo relay (ex.: trocar o
Wi-Fi), PGM temporizada, sirene `40 19` com alarme tocando, pareamento de sensor
sem fio, e os caminhos de firmware do módulo ESP8266.

Mapa detalhado, status de cada item e testes abertos: **[docs/STATUS.md](docs/STATUS.md)**.

## Componentes

| Caminho | O que é |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | Especificação do protocolo (controle + config) |
| [`relay/elc_local_relay.py`](relay/elc_local_relay.py) | Relay local — a central conecta nele no lugar da nuvem |
| [`tools/setup_ap.sh`](tools/setup_ap.sh) | Transforma um Linux em gateway/AP para a central |
| [`tools/relay_tap.py`](tools/relay_tap.py) | Proxy transparente com log (observa central⇄nuvem) |
| [`tools/decode_capture.py`](tools/decode_capture.py) | Decodifica um `.pcap` (mascara SSID/senha) |
| [`docs/redirecionamento.md`](docs/redirecionamento.md) | Como redirecionar a central para o relay + gargalos |
| [`docs/homeassistant.md`](docs/homeassistant.md) | Uso com Home Assistant (local via MQTT, sem nuvem) |
| [`docs/firmware.md`](docs/firmware.md) | Mexer no firmware do módulo Wi-Fi (ESP8266): caminhos, limites e riscos |
| [`docs/STATUS.md`](docs/STATUS.md) | Estado item a item (o que é confirmado × não testado) e testes abertos |
| [`CHANGELOG.md`](CHANGELOG.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) | Marcos do projeto · como contribuir |
| [`elc6012net_local/`](elc6012net_local) · [`elc6012net_hibrido/`](elc6012net_hibrido) | Apps do Home Assistant (Local validado · Híbrido experimental) |

## Caminho rápido

1. Redirecione o servidor da nuvem para o relay (DNS ou DNAT — ver
   [docs/redirecionamento.md](docs/redirecionamento.md)); para laboratório,
   `tools/setup_ap.sh` cria uma rede só para a central.
2. Rode o relay e abra o painel:
   ```bash
   python3 relay/elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 --web 8088 --tz America/Sao_Paulo
   # painel: http://127.0.0.1:8088  (aciona a cerca — só local)
   ```
3. Controle pelo painel web (arme/desarme/choque) ou pelo stdin
   (`shockon`, `arm`, `allon`…). O status aparece ao vivo conforme a central muda.

Capturar/decodificar tráfego para estudar o protocolo: `tools/decode_capture.py captura.pcap`.

## ⚠️ Segurança das capturas

Um `.pcap` da central contém, **em texto claro**, o SSID e a **senha do seu
Wi-Fi** (bloco de config `02 c0`) e o MAC da central. O `.gitignore` já bloqueia
`*.pcap`. **Nunca** publique capturas cruas; use `decode_capture.py`, que mascara
esses dados.

## Créditos

Baseado em [rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net),
que mapeou o protocolo app⇄nuvem e criou o add-on Home Assistant. Os opcodes de
controle foram cruzados com [bobaoapae/guardian-api-intelbras](https://github.com/bobaoapae/guardian-api-intelbras)
(cliente de nuvem + Home Assistant) — ver §7 do [PROTOCOL.md](PROTOCOL.md). O lado
servidor (relay local, sem nuvem) é a peça que este projeto acrescenta.

## Licença

MIT — ver [LICENSE](LICENSE).
