# Status & roadmap

Estado da engenharia reversa. **Contribuições são bem-vindas** — se você tem um
ELC 6012 NET, pode rodar os testes abertos e mandar a captura (veja
[CONTRIBUTING](../CONTRIBUTING.md)).

> Trabalho ainda não validado ao vivo (painel web, modo HA local) fica na branch
> **`experimental`**; ao validar, entra na `main`.

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
| Keepalive `f0 f1`/`f0 fd` | ✅ | **servidor pinga `f0 f1`, central responde `f0 fd`/`f0 fe`**; relay pinga proativamente |
| Registro `3f 94` | ✅ | MAC + modelo, sem auth |
| Pânico `40 1a 01` | ✅ | dispara emergência; confirmado. `40 1a 00` observado, efeito não confirmado |
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
| Keepalive `f0 f1` proativo | ✅ **validado ao vivo**: relay pinga, sessão fica de pé (6+ min) |
| Status ao vivo (sem nuvem) | ✅ **validado ao vivo**: choque/alarme/zonas/disparo/relógio/RSSI reais |
| Comandos (arme/choque) via relay | 🟡 corrigido: sessão de leitura dava NACK no `40 1e`; agora usa a sessão de controle — falta re-testar efeito físico |
| Bypass / PGM / pânico via relay | ⬜ implementado; falta validar ao vivo |
| Integração MQTT → Home Assistant local | ⬜ planejado |
| Interface web (painel no relay) | 🟡 implementada (`--web`); falta validar ao vivo |

---

## Testes abertos (como ajudar)

Com a central conectada a um gateway sob seu controle (ver
[`tools/setup_ap.sh`](../tools/setup_ap.sh)) e `tcpdump` capturando a porta 9009,
faça a ação pelo app **anotando a hora** e mande a captura decodificada
(`tools/decode_capture.py`, que já mascara segredos).

1. ~~Bypass `40 1f`~~ ✅ confirmado.
2. **PGM temporizada** — mude os segundos de uma PGM (0 → N → 0).
3. **Parear sensor sem fio** — com a central **desarmada**, cadastre um sensor.
4. **Validar o relay local** — rode o `relay/elc_local_relay.py`, redirecione a
   central para ele e confirme arme/desarme/choque **sem nuvem**.
