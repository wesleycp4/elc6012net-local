# Status & roadmap

Estado da engenharia reversa. **Contribuições são bem-vindas** — se você tem um
ELC 6012 NET, pode rodar os testes abertos e mandar a captura (veja
[CONTRIBUTING](../CONTRIBUTING.md)).

Legenda: ✅ confirmado · 🟡 parcial · ⬜ aberto (precisa de teste)

## Controle / monitoração
| Item | Status | Observação |
|---|---|---|
| Registro da central (sem auth) | ✅ | MAC + modelo |
| Sincronismo de hora (BCD) | ✅ | |
| Status `0b 4a` (164 bytes) | ✅ | choque, alarme, zonas, bypass, relógio |
| Arme/desarme/choque `40 1e` | ✅ | partições 1 / 2 / 255 |
| Eventos `10 b2` | 🟡 | chega e é confirmado; faltam decodificar todos os códigos |
| Sinal Wi-Fi `[163]` (RSSI com sinal) | 🟡 | consistente, falta medição independente |
| **Bypass `40 1f`** | ⬜ | **teste aberto** (ver abaixo) |

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
| Enquadramento (leitura/escrita de frames) | ✅ validado contra frames reais |
| Registro + hora | 🟡 implementado, falta validar ao vivo |
| Abertura de sessão `f0 f0` | ⬜ **payload não decodificado** — sem ela, poll/comando provavelmente são ignorados |
| Status + comando | 🟡 implementado, depende da sessão acima |
| Bypass / PGM / config via relay | ⬜ depende dos testes acima |
| Integração MQTT → Home Assistant local | ⬜ planejado |
| Interface web | ⬜ planejado |

---

## Testes abertos (como ajudar)

Com a central conectada a um gateway sob seu controle (ver
[`tools/setup_ap.sh`](../tools/setup_ap.sh)) e `tcpdump` capturando a porta 9009,
faça a ação pelo app **anotando a hora** e mande a captura decodificada
(`tools/decode_capture.py`, que já mascara segredos).

1. **Bypass `40 1f`** — anule e reative uma zona pelo app.
2. **PGM temporizada** — mude os segundos de uma PGM (0 → N → 0).
3. **Parear sensor sem fio** — com a central **desarmada**, cadastre um sensor.
4. **Validar o relay local** — rode o `relay/elc_local_relay.py`, redirecione a
   central para ele e confirme arme/desarme/choque **sem nuvem**.
