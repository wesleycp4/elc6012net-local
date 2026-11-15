# Protocolo ELC 6012 NET — central ⇄ nuvem (relay AMT8000)

Documentação do protocolo que o eletrificador **Intelbras ELC 6012 NET** usa para
falar com a nuvem Intelbras (relay `amt8000`), obtida por **engenharia reversa via
captura de rede** do próprio equipamento, a partir da base de
[rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net) (TCP 9009, **texto claro, sem TLS**).

O objetivo é permitir **controle 100% local, sem nuvem**: um servidor que faz o
papel do relay, ao qual a central se conecta (ver [`relay/`](relay/)).

> MAC dos exemplos é fictício (`00:1A:3F:12:34:56`). Status de cada item:
> ✅ confirmado em captura · 🟡 parcial / inferido · ⬜ ainda a validar.

---

## 1. Arquitetura

A central mantém uma conexão TCP **de saída, permanente**, com o relay. O app
(ou um cliente) conecta no mesmo relay e é roteado até a central pelo MAC. Na LAN
a central só responde a sondas de descoberta na porta 9009 (segundo o projeto
rhacius); **todo o controle passa pelo relay**. Dois servidores (porta 9009):

1. `amt.intelbras.com.br` — servidor "geral" (informa em qual relay o painel está)
2. `amt8000.intelbras.com.br` — relay onde a sessão acontece (ex.: `52.67.212.35`)

**Nenhuma autenticação do servidor.** ✅ (a *sessão de app* tem sua própria abertura, §3.4) A central se registra mandando só o MAC +
modelo; o relay responde `f0 fe` (ok) e segue. Não há TLS, nem token, nem desafio
que a central valide. **Consequência: se a central conectar no seu servidor, ele é
aceito** — é o que torna o controle local viável.

---

## 2. Enquadramento

Frames de controle:

```
[sessão : 4 bytes][tam : 2 bytes BE][payload : tam bytes][checksum : 1 byte]
total = 7 + tam     checksum = XOR(todos os bytes anteriores) ^ 0xFF
```

- `sessão` = **índice da sessão de app**, não um contador por mensagem. ✅ Vale
  `00 00 00 00` na conexão base (registro, hora, tiques `f0 fe`) e `00 00 00 0N`
  durante a sessão de app N (N=1 na 1ª sessão; vira 02, 03… se a sessão reabrir).
  Dentro de uma sessão o índice é **fixo**: `f0 f0`, `0b 4a`, `40 1e`, `f0 f1`
  todos usam o mesmo `00 00 00 0N`. A central ecoa com os dois primeiros bytes
  trocados (`00 00 00 01` do relay ⇄ `00 01 00 00` da central).
- **Exceção — resposta de status (`0b 4a`):** o campo `tam` vale o total (164) e
  **não há checksum** nesse firmware (placa 1.1.0 / módulo 1.2.11). Outros
  firmwares mandam 165 com checksum. 🟡 (ver §4.1 do projeto rhacius)
- **Checksum só nos frames que o relay envia.** ✅ (confirmado ao vivo) O XOR^0xFF
  acima vale para relay→central; nos frames que a **central** manda ele **não
  bate** (ex.: `f0 fe` vem com `f1`, mas o XOR^0xFF daria `f2`), e o status 164B
  nem tem checksum. O relay por isso **nunca valida** o checksum recebido.
- **Enquadramento por re-sincronização.** ✅ A central às vezes manda `f0 fd`/`f0 fe`
  com um byte `00` a mais, mas mantém o campo `tam`=`00 02` — então `7+tam`
  consome 1 byte a menos. Como o checksum não serve de âncora, o relay valida o
  **cabeçalho** de cada frame (`00 0N 00 00` + comando conhecido) e, se o próximo
  byte não for um cabeçalho válido, descarta-o e realinha. Um `f0 fd`/`f0 fe`
  fica no máximo 1 byte torto (é só ack), e status/eventos/comandos voltam a cair
  certos. Validado contra o tráfego do teste ao vivo (146 frames, 92 status).

Exemplos reais (✅):

| Frame | Bytes |
|---|---|
| ack ok | `00 00 00 00 00 02 f0 fe f3` |
| poll de status | `00 00 00 01 00 02 0b 4a bd` |
| comando choque ON | `00 00 00 01 00 04 40 1e 02 01 a7` |

---

## 3. Handshake de sessão (central ⇄ relay)

Ordem observada ao conectar (✅):

1. **Registro** (central→relay): comando `3f 94` — `3f 94 45 00 00 <MAC:6> <modelo> 01 01 …`
   → relay responde `f0 fe` (ok). Sem senha/token. ✅
2. **`f0 f7`** (central) → `f0 fe` (relay).
3. **Hora** (central pede `f0 80 03`) → relay responde
   `f0 80 <AA MM DD DS hh mm ss>` em **BCD** (DS = dia da semana) (ex.: `26 11 13 06 08 18 04`). ✅
4. **Abertura de sessão de app** (`f0 f0`) ✅ — antes de pedir status ou mandar
   comando, o relay abre uma sessão de índice N enviando, na sessão `00 00 00 0N`:
   `f0 f0 01 <dígitos do código> 10 00`; a central confirma com `f0 f0 00 <ck>` na
   sessão `00 0N 00 00`. **Sem essa abertura, a central ignora poll e comando.**

   ⚠️ **O código de acesso vai em texto claro**, um dígito por byte (ex.: um código
   de 6 dígitos ocupa 6 bytes entre o prefixo `01` e o sufixo `10 00`). Por isso o
   código fica exposto na captura; o relay recebe o código em tempo de execução
   (`--code`), nunca embutido.
5. **Keepalive de sessão** ✅ — **quem pinga é o servidor** (nuvem/relay). Durante
   a sessão ele envia `f0 f1` (na sessão de app `00 00 00 0N`) e a central responde
   `f0 fd` ou `f0 fe` ~0,1–0,8 s depois. Na conexão base (`00 00 00 00`) o servidor
   também emite `f0 fe` como tique periódico. Ou seja, o relay precisa **pingar
   proativamente**; a central não inicia keepalive, só responde. (Modelo invertido
   — relay respondendo `f0 f1` a um `f0 fd` da central — não mantém a sessão.)

---

## 4. Controle e monitoração

### 4.1 Status — comando `0b 4a`  ✅
Relay manda `00 00 00 01 00 02 0b 4a bd`; central responde **164 bytes**.
Offsets confirmados (0-based, a partir do byte 0 do frame):

| Offset | Campo |
|---|---|
| `[8]` | modelo (`0x35` = ELC 6012 NET) |
| `[30]` bit0 | choque ligado |
| `[31]` bit0 | alarme armado |
| `[46..47]` | zonas abertas (bitmap) |
| `[54..55]` | zonas disparadas (bitmap) |
| `[62..63]` | zonas em bypass (bitmap) |
| `[72..77]` | relógio: dia mês ano hh mm ss (hex) |
| `[163]` | sinal Wi-Fi: RSSI; se `>127`, ler como negativo (`256 - v` = \|dBm\|) 🟡 |

### 4.2 Arme / desarme / choque — comando `40 1e`  ✅
Relay→central: `40 1e <partição> <modo>`.

| Partição | Modo | Efeito |
|---|---|---|
| `01` | `01`/`00` | alarme liga / desliga |
| `02` | `01`/`00` | choque liga / desliga |
| `ff` | `01`/`00` | ambos (partição 255) liga / desliga |

No ELC o 2º byte observado é liga/desliga (`01`/`00`). Em centrais de alarme AMT o
mesmo comando codifica o modo de arme (0=desarma, 1=total, 2=parcial/stay,
3=forçado) — ver §7; não testado no ELC.

### 4.3 Bypass de zona — comando `40 1f`  ✅
Relay→central: `40 1f ff <z1 z2 z3 z4 z5 z6 z7 z8>`, um byte por zona
(`01` = anulada, `00` = normal). O `ff` inicial é o seletor de partição (todas),
igual ao `40 1e`. Ex.: `40 1f ff 00 00 01 00 00 00 00 00` anula só a zona 3.

### 4.4 Histórico de eventos — comando `39 00`  ✅
Relay→central: `39 00 <página 0..7>`; a central responde com a página de eventos,
cada registro com 15 bytes = código Contact-ID (9B) + timestamp `DD MM YY HH MM SS`.

### 4.5 Pânico — comando `40 1a`  ✅
Relay→central: `40 1a <tipo>`. O segundo byte é o **tipo de pânico** (não é
liga/desliga):

| Tipo | Efeito |
|---|---|
| `00` | pânico **silencioso** (sem sirene; alerta ao monitoramento) |
| `01` | pânico **audível** (dispara a sirene) |
| `02` | fogo (só família AMT 8000) |
| `03` | emergência médica (só família AMT 8000) |

Nosso teste confirmou o `01` (disparo audível, vídeo + mapa3). O `40 1a 00`
apareceu na captura mapa e bate com o tipo "silencioso" (daí não ter efeito
visível). A tabela de tipos foi validada cruzando com a eng. reversa do APK em
`bobaoapae/guardian-api-intelbras` (ver §7). O relay usa `01` por padrão.

### 4.6 Acionar PGM — comando `45 af`  ✅
Relay→central: `45 af <pgm> <estado>`, PGM **base-0** (`00` = PGM1, `01` = PGM2),
estado `01` = liga / `00` = desliga. Ex.: `45 af 00 01` liga a PGM1. A central só
aceita se a PGM estiver no modo "acesso via app" (senão responde com erro).
PGM = saída programável (contato que aciona um aparelho externo: portão, luz…).

### 4.7 Eventos — comando `10 b2`  ✅
Central→relay empurra eventos (disparo, arme, desarme, energia…) no padrão
Contact-ID, com dois timestamps. Relay responde `f0 fe`. É o que gera as
notificações. Decodificação detalhada de cada código: 🟡 (parcial).

### 4.8 Desligar sirene — comando `40 19`  ⬜
Relay→central: `40 19` silencia a sirene sem desarmar. Byte do comando conhecido
pela eng. reversa do APK (`bobaoapae`, ver §7); **não testado no ELC** — falta
confirmar payload/efeito em captura.

---

## 5. Configuração — leitura/escrita de blocos  ✅

A configuração **não é um protocolo à parte**: é leitura/escrita de blocos de
memória, mesmo enquadramento.

- **Ler**: relay→central `3f 12 <addr:2> <tam:2>` → central responde com os dados.
- **Gravar**: relay→central `2f 12 <addr:2> <tam:2> <dados:tam>`.

### Mapa de blocos (✅ confirmado por captura)

| Endereço | Tam | Conteúdo |
|---|---|---|
| `00 00` | 128 | **Zonas**: 8 × 16 bytes = `[attr][nome 15 chars]` |
| `02 b0` | 16 | **Nome do eletrificador** |
| `02 c0` | 96 | **Config Wi-Fi** (SSID + senha, **texto claro** ⚠️) |
| `03 e0` | 32 | **Config geral** (abaixo) |
| `04 00` | 420 | **Usuários** (nomes) |

### Bloco `00 00` — atributo de zona (bitfield)  ✅

| Bit | Atributo |
|---|---|
| `0x01` | habilitada |
| `0x02` | inteligente |
| `0x04` | temporizada |
| `0x10` | silenciosa |
| `0x20` | parcial |
| `0x40` | 24 horas |

### Bloco `03 e0` — config geral (offsets dentro dos dados)  ✅

| Offset | Campo |
|---|---|
| `[3]` | pulsos falhos (ex.: `0a`=10, `0f`=15) |
| `[7]` | modo PGM1: disparo=`00`, acesso app=`01`, espelho sirene=`02` |
| `[11]` | modo PGM2: cerca=`00`, acesso app=`01`, espelho sirene=`02` |
| `[14]` | reportagem em tempo real (`01`/`00`) |
| `[8]`,`[12]` | PGM temporizada (segundos) — 🟡 a confirmar |

---

## 7. Validação cruzada e referências

Dois projetos independentes de engenharia reversa do mesmo ecossistema
corroboram o mapeamento acima — úteis como conferência e para o que ainda falta:

- **`bobaoapae/guardian-api-intelbras`** (MIT) — *cliente* da nuvem Intelbras
  (OAuth + ISECNet) com integração Home Assistant. Da eng. reversa do APK, os
  opcodes V2 batem com os nossos: `40 1e` arme, `0b 4a` status, `40 1a` pânico,
  `40 1f` bypass, `45 af` PGM, `f0 f0` autorização, e o **checksum XOR^0xFF é o
  mesmo**. Também confirma os **tipos de pânico** (§4.5) e traz comandos que
  ainda não testamos no ELC (`40 19` desliga sirene, modos de arme). Ele é um
  cliente que *disca para a nuvem*; não emula o servidor. O item "ISECNet local
  (sem relay da nuvem)" é roadmap **em aberto** lá — ou seja, o relay/servidor
  local deste projeto é justamente a peça que falta para controle 100% local.
- **`rhacius/ha-elc6012net`** — base original do add-on de nuvem para o ELC 6012
  NET (ver README e LICENSE).

O que é específico deste projeto: o **lado servidor** — emular a nuvem para a
central conectar localmente (enquadramento, abertura de sessão com código,
keepalive, status 164B sem checksum, blocos de config) — validado byte a byte
contra capturas reais do ELC 6012 NET (placa 1.1.0 / módulo 1.2.11).
