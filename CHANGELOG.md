# Changelog

Marcos do projeto. Datas no formato AAAA-MM-DD. Para o estado item a item, ver
[docs/STATUS.md](docs/STATUS.md).

## 2026-11-16 — Validação ao vivo e organização

- **Controle e monitoração validados ao vivo** pelo relay, sem nuvem: arme/desarme,
  choque, "tudo ligado/desligado", status, bits de zona e eventos.
- **Home Assistant** via MQTT confirmado ao vivo (arme/desarme e cerca pelo HA).
- **Protocolo:** eventos `10 b2` (Contact-ID) decodificados; `f0 fd 00` identificado
  como ACK (não recusa); `40 1a` fogo/médico recusados no ELC; PGM só no modo app;
  bits de zona/disparo/bypass confirmados; MAC no status `[157..162]`.
- **Servidor é fixo no firmware:** varredura de toda a memória de config (`3f 12`)
  não achou o endereço — o redirecionamento na rede é obrigatório
  ([docs/redirecionamento.md](docs/redirecionamento.md)).
- **Relay:** `f0 fd 00` não dispara mais reenvio; `40 1e` conferido pelo status;
  `--tz` (evita hora errada com o relay em UTC); `control()` serializado.
- **Apps do HA:** Local 1.0.1, Híbrido 0.1.2 (opção `inject_session`).
- **Hardware:** módulo Wi-Fi ESP8266 (ESP-WROOM-02D) documentado; caminhos de
  firmware em [docs/firmware.md](docs/firmware.md).
- **Modo híbrido (experimental):** túnel e comando local funcionam, mas o app oficial
  não reconectou no teste — **pendente**.

## 2026-11 — Base

- Engenharia reversa do protocolo central ⇄ nuvem (TCP 9009, texto claro, sem auth
  de servidor) — ver [PROTOCOL.md](PROTOCOL.md).
- Relay local (`relay/elc_local_relay.py`) e ferramentas de captura (`tools/`).
- Integração Home Assistant via MQTT Discovery e empacotamento como Apps do HA.
- Baseado em [rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net),
  cruzado com [bobaoapae/guardian-api-intelbras](https://github.com/bobaoapae/guardian-api-intelbras).
