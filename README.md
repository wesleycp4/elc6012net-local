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

## Estado atual

- ✅ **Protocolo de controle** mapeado (registro, status de 164 bytes,
  arme/desarme/choque, eventos) — ver [PROTOCOL.md](PROTOCOL.md).
- ✅ **Protocolo de configuração** mapeado (zonas + atributos, nome, pulsos falhos,
  PGMs, usuários, Wi-Fi) — é leitura/escrita de blocos de memória.
- 🟡 **Relay local** (`relay/elc_local_relay.py`): protótipo com enquadramento
  validado contra frames reais; **falta validar ao vivo** e implementar a
  abertura de sessão (`f0 f0`), ainda não decodificada.
- ⬜ Bypass, PGM temporizada, pareamento de sensor, MQTT→HA, interface web.

Mapa completo e testes abertos: **[docs/STATUS.md](docs/STATUS.md)**.

## Componentes

| Caminho | O que é |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | Especificação do protocolo (controle + config) |
| [`relay/elc_local_relay.py`](relay/elc_local_relay.py) | Relay local — a central conecta nele no lugar da nuvem |
| [`tools/setup_ap.sh`](tools/setup_ap.sh) | Transforma um Linux em gateway/AP para a central |
| [`tools/relay_tap.py`](tools/relay_tap.py) | Proxy transparente com log (observa central⇄nuvem) |
| [`tools/decode_capture.py`](tools/decode_capture.py) | Decodifica um `.pcap` (mascara SSID/senha) |
| [`docs/homeassistant.md`](docs/homeassistant.md) | Uso com Home Assistant (hoje via nuvem; local no roadmap) |

## Caminho rápido

1. Ponha a central numa rede sob seu controle e capture o tráfego (`tools/setup_ap.sh`).
2. Decodifique com `tools/decode_capture.py captura.pcap`.
3. Rode o relay local e redirecione a central para ele (instruções em `relay/`).

## ⚠️ Segurança das capturas

Um `.pcap` da central contém, **em texto claro**, o SSID e a **senha do seu
Wi-Fi** (bloco de config `02 c0`) e o MAC da central. O `.gitignore` já bloqueia
`*.pcap`. **Nunca** publique capturas cruas; use `decode_capture.py`, que mascara
esses dados.

## Créditos

Baseado em [rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net),
que mapeou o protocolo app⇄nuvem e criou o add-on Home Assistant.

## Licença

MIT — ver [LICENSE](LICENSE).
