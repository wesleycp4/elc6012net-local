# Status & roadmap

Estado da engenharia reversa. **Contribuições são bem-vindas** — se você tem um
ELC 6012 NET, pode rodar os testes abertos e mandar a captura (veja
[CONTRIBUTING](../CONTRIBUTING.md)).

> `main` tem o núcleo validado (controle local + integração HA via MQTT).
> A `experimental` fica à frente com trabalho ainda não testado ao vivo
> (ex.: modo proxy/híbrido com a nuvem), antes de mesclar.

Legenda: ✅ confirmado · 🟡 parcial · ⬜ aberto (precisa de teste)

## Controle / monitoração
| Item | Status | Observação |
|---|---|---|
| Registro da central (sem auth) | ✅ | MAC + modelo |
| Sincronismo de hora (BCD) | ✅ | hora **local** (a nuvem manda Brasília); relay com `--tz` |
| Portas / reconexão | ✅ | 9009; na falha alterna 9009 ⇄ 8080 a cada ~11 s e refaz o DNS |
| Status `0b 4a` (164 bytes) | ✅ | choque, alarme, zonas, disparo, bypass, relógio, MAC `[157..162]` |
| Bits de zona (aberta/disparo/bypass) | ✅ | byte 46/54/62 bit0 = zona 1 … bit7 = zona 8 (ao vivo) |
| Arme/desarme/choque `40 1e` | ✅ | partições 1 / 2 / 255; armar o alarme não liga o choque |
| Eventos `10 b2` | ✅ | Contact-ID decodificado (layout + códigos 407/409/130/120/122/422/306/410/412, PROTOCOL §4.7) |
| Histórico `39 00` | ✅ | leitura por página; registro = Contact-ID + timestamp |
| Manter sessão (`f0 f7`→`f0 fe`) | ✅ | central pinga `f0 f7`, servidor responde `f0 fe`; **`f0 f1` é DISCONNECT, nunca enviar** |
| Registro `3f 94` | ✅ | MAC + modelo, sem auth |
| Pânico `40 1a <tipo>` | ✅ | `00` silencioso e `01` audível (ao vivo, eventos 122/120); `02` fogo e `03` médico **recusados no ELC** (`0x21`) |
| Acionar PGM `45 af` | ✅ | `45 af <pgm base-0> <estado>`; só no modo "acesso via app" (fora dele: `0x21`, confirmado ao vivo) |
| Sinal Wi-Fi `[163]` (RSSI com sinal) | 🟡 | consistente, falta medição independente |
| Bypass `40 1f` | ✅ | `40 1f ff <z1..z8>`, confirmado ao vivo pelo relay (bitmap `[62..63]`) |
| Desligar sirene `40 19` | 🟡 | aceito pela central; falta testar com a sirene tocando |
| Resposta `f0 fd 00` | ✅ | é **ACK**, não recusa (recusa real: `0x21`, `0x3f`) |

## Configuração (blocos `3f 12` ler / `2f 12` gravar)
| Bloco | Status | Observação |
|---|---|---|
| `00 00` zonas (nome + attr bitfield) | ✅ | habilitada/inteligente/temporizada/silenciosa/parcial/24h |
| `02 b0` nome do eletrificador | ✅ | |
| `03 e0` pulsos falhos, PGM1/PGM2 modo, reportagem | ✅ | |
| `03 e0` PGM temporizada (segundos) | 🟡 | offset a confirmar |
| `02 c0` Wi-Fi (SSID+senha) | ✅ | texto claro |
| **Trocar a rede Wi-Fi** (`2f 12 02 c0`) | 🟡 | gravação mapeada (SSID+senha); efeito via relay a testar |
| `04 00` usuários (nomes/código) | ✅ | código em texto claro no bloco |
| Opcodes extras (`38 5b`/`38 5c`/`0b 01`/`46 a0`/`46 10`/`00 60`) | 🟡 | testados ao vivo: consultas/refresh, nenhum aciona nada (PROTOCOL §6) |
| `3f aa` pedir MAC | ✅ | este firmware **não responde**; o MAC vem no status |
| Endereço do servidor na config | ✅ | **não existe**: varredura de toda a memória (`3f 12`) sem `amt8000`/`intelbras` |
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
| Bypass / PGM / pânico via relay | ✅ **validado ao vivo** (PGM só no modo app) |
| Confirmação de comando | ✅ `f0 fd 00` tratado como ACK; `40 1e` conferido no status e reenviado se não mudou |
| Integração MQTT → Home Assistant local | ✅ **validado ao vivo**: entidades criadas; arme/desarme e cerca pelo HA |
| Modo híbrido/proxy (`experimental`) | 🟡 túnel e injeção local funcionam; o app oficial **não entrou** no teste (ver abaixo) |

---

## Testes abertos (como ajudar)

Com a central conectada a um gateway sob seu controle (ver
[`tools/setup_ap.sh`](../tools/setup_ap.sh)) e `tcpdump` capturando a porta 9009,
faça a ação pelo app **anotando a hora** e mande a captura decodificada
(`tools/decode_capture.py`, que já mascara segredos).

1. **Modo híbrido** (branch `experimental`) — no teste de 16/11 o túnel funcionou
   (registro, hora e keepalive da nuvem passaram; comando local na sessão 2 sem
   derrubar a nuvem), mas o app oficial não entrou em ~3 min. A versão atual não
   repassa mais à nuvem as respostas da sessão injetada. Falta: rodar mais tempo,
   capturar **também o lado da nuvem** (interface de saída) e anotar a hora em que
   o app tenta entrar.
   Atenção: a nuvem dá um índice de sessão por cliente (ponte de nuvem do HA = 1,
   app do celular = 2…), e a injeção usa a 2 por padrão — com mais de um cliente
   ligado, use um índice livre (`--inject-session`, na `experimental`).
2. **Sirene `40 19`** — com o alarme disparado e a sirene ligada.
3. **PGM temporizada** — mude os segundos de uma PGM (0 → N → 0).
4. **Parear sensor sem fio** — com a central **desarmada**, cadastre um sensor.
5. **Código de evento em aberto** (412) — acione a função anotando a
   hora e confira o evento `10 b2`.
