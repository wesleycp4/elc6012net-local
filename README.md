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

## ⚠️ Requisito: redirecionar a central

A central tem o servidor da nuvem **fixo no firmware** (`amt8000.intelbras.com.br`,
porta 9009) e não há configuração para trocá-lo. Para usar qualquer modo local —
inclusive o **Híbrido** — você precisa fazer esse nome apontar para o relay na sua
rede: DNS local no roteador, AdGuard Home/Pi-hole, uma rede só para a central ou
DNAT. **Sem controle do DNS/rede, o modo local não funciona** (resta a integração
via nuvem). Opções, como testar e gargalos:
**[docs/redirecionamento.md](docs/redirecionamento.md)**.

## Estado atual

- ✅ **Controle local confirmado ao vivo, sem nuvem**: a central conecta no relay e
  responde a arme/desarme, choque e "tudo ligado/desligado" — validado fisicamente.
- ✅ **Protocolo de controle** mapeado (registro, abertura de sessão `f0 f0`, status
  de 164 bytes, `40 1e`, bypass, pânico, PGM, eventos Contact-ID decodificados) —
  ver [PROTOCOL.md](PROTOCOL.md).
- ✅ **Protocolo de configuração** mapeado (zonas + atributos, nome, pulsos falhos,
  PGMs, usuários, Wi-Fi) — leitura/escrita de blocos de memória.
- ✅ **Relay local** (`relay/elc_local_relay.py`): enquadramento com re-sincronização,
  sessão de controle, status ao vivo, painel web e retry automático na recusa.
- ✅ **Integração Home Assistant local** via MQTT Discovery (`relay/mqtt_bridge.py`),
  **validada ao vivo** (arme/desarme e cerca pelo HA, zonas 1–8 com bits
  confirmados) — ver [docs/homeassistant.md](docs/homeassistant.md).
  Também empacotado como **App do Home Assistant**: adicione este repositório na
  loja de Apps e instale o **ELC 6012 NET Local** (o **Híbrido** é experimental).
- 🟡 Modo **híbrido** (manter o app Intelbras junto): túnel e comando local
  funcionam, mas o app oficial não entrou no teste — segue na `experimental`.
- ⬜ Pareamento de sensor sem fio, PGM temporizada, sirene `40 19` com alarme tocando.

Mapa completo e testes abertos: **[docs/STATUS.md](docs/STATUS.md)**.

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
