# Status & roadmap

Estado da engenharia reversa. **Contribuições são bem-vindas** — se você tem um
ELC 6012 NET, pode rodar os testes abertos e mandar a captura (veja
[CONTRIBUTING](../CONTRIBUTING.md)).

> As branches `main` e `experimental` estão sincronizadas. Trabalho em curso
> (ex.: integração HA local) pode ficar na `experimental` antes de validar.

Legenda: ✅ confirmado · 🟡 parcial · ⬜ aberto (precisa de teste)

## Controle / monitoração
| Item | Status | Observação |
|---|---|---|
| Registro da central (sem auth) | ✅ | MAC + modelo |
| Sincronismo de hora (BCD) | ✅ | |
| Status `0b 4a` (164 bytes) | ✅ | choque, alarme, zonas, bypass, relógio |
| Arme/desarme/choque `40 1e` | ✅ | partições 1 / 2 / 255 |
| Eventos `10 b2` | 🟡 | chega e é confirmado; faltam decodificar todos os códigos |
| Histórico `39 00` | ✅ | leitura por página; registro = Contact-ID + timestamp |
| Manter sessão (`f0 f7`→`f0 fe`) | ✅ | central pinga `f0 f7`, servidor responde `f0 fe`; **`f0 f1` é DISCONNECT, nunca enviar** |
| Registro `3f 94` | ✅ | MAC + modelo, sem auth |
| Pânico `40 1a <tipo>` | ✅ | `01`=audível (confirmado), `00`=silencioso, `02`=fogo, `03`=médico (cross-val. bobaoapae) |
| Acionar PGM `45 af` | ✅ | `45 af <pgm base-0> <estado>`; confirmado (PGM no modo app) |
| Sinal Wi-Fi `[163]` (RSSI com sinal) | 🟡 | consistente, falta medição independente |
| Bypass `40 1f` | ✅ | `40 1f ff <z1..z8>`, confirmado em captura |

## Configuração (blocos `3f 12` ler / `2f 12` gravar)
| Bloco | Status | Observação |
|---|---|---|
| `00 00` zonas (nome + attr bitfield) | ✅ | habilitada/inteligente/temporizada/silenciosa/parcial/24h |
| `02 b0` nome do eletrificador | ✅ | |
| `03 e0` pulsos falhos, PGM1/PGM2 modo, reportagem | ✅ | |
| `03 e0` PGM temporizada (segundos) | 🟡 | offset a confirmar |
| `02 c0` Wi-Fi (SSID+senha) | ✅ | texto claro |
| `04 00` usuários (nomes) | ✅ | PINs não localizados em claro |
| Parear sensor sem fio | ⬜ | **teste aberto** (precisa central desarmada) |

## Relay local
| Item | Status |
|---|---|
| Enquadramento (leitura/escrita de frames) | ✅ **validado ao vivo**; resync por cabeçalho (lida com variante f0fd/f0fe +1 byte) |
| Registro + hora | ✅ **validado ao vivo** (central registra, pede hora, recebe) |
| Abertura de sessão de controle `f0 f0` | ✅ **validado ao vivo**: payload fixo `f0 f0 03 03 06 05 09 00 00 00 01` (sem código) |
| Manter a sessão | ✅ responder o `f0 f7` da central + polls; **nunca** mandar `f0 f1` (=DISCONNECT) |
| Status ao vivo (sem nuvem) | ✅ **validado ao vivo**: choque/alarme/zonas/disparo/relógio/RSSI reais |
| **Comandos (arme/desarme/choque/tudo) via relay** | ✅ **validado ao vivo (física)**: reabre a sessão + `40 1e`; retry automático na recusa |
| Reconexão (churn de WiFi) | ✅ reset de buf/sessão por conexão; threads atadas à conexão |
| Detecção de recusa (NACK `f0 fd <code>`) | ✅ loga `[RECUSADO] code 0xNN` e reenvia (até 2x) |
| Interface web (painel no relay) | ✅ **validado ao vivo**: via principal de controle (arme/desarme/choque) |
| Bypass / PGM / pânico via relay | 🟡 implementados; faltam testes ao vivo |
| Integração MQTT → Home Assistant local | ⬜ planejado |

---

## Testes abertos (como ajudar)

Com a central conectada a um gateway sob seu controle (ver
[`tools/setup_ap.sh`](../tools/setup_ap.sh)) e `tcpdump` capturando a porta 9009,
faça a ação pelo app **anotando a hora** e mande a captura decodificada
(`tools/decode_capture.py`, que já mascara segredos).

1. ~~Bypass `40 1f`~~ ✅ confirmado.
2. ~~Validar o relay local (arme/desarme/choque sem nuvem)~~ ✅ **confirmado ao vivo**.
3. **PGM temporizada** — mude os segundos de uma PGM (0 → N → 0).
4. **Parear sensor sem fio** — com a central **desarmada**, cadastre um sensor.
5. **Bypass / PGM / pânico via relay** — confirme o efeito físico pelo relay.
