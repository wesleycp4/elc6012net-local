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
rhacius); **todo o controle passa pelo relay**. Dois servidores:

1. `amt.intelbras.com.br` — servidor "geral" (informa em qual relay o painel está)
2. `amt8000.intelbras.com.br` — relay onde a sessão acontece (ex.: `52.67.212.35`)

O nome `amt8000.intelbras.com.br` é **fixo no firmware** ✅: nas capturas ele só
aparece nas consultas DNS da central, e uma varredura de **toda** a memória de
config (`3f 12`, 0x0000–0xfff0) não achou `amt8000`, `intelbras`, `.com`, `9009`
nem `8080`. Não há comando para trocá-lo; para usar um relay local é preciso
redirecioná-lo na rede (ver [docs/redirecionamento.md](docs/redirecionamento.md)).

**Portas e reconexão** ✅ (captura do laboratório): a central conecta na porta
**9009**; se a conexão falhar ou cair, ela **alterna entre 9009 e 8080** a cada
~11 s (a nuvem atende nas duas) e **refaz a consulta DNS** a cada ciclo de
reconexão. Um relay/DNAT deve cobrir as duas portas (ou só a 9009, aceitando que a
central leve uma tentativa a mais para achá-lo).

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
  durante a sessão de app N. A nuvem dá **um índice por cliente conectado**: nas
  capturas com a ponte de nuvem do HA e o app do celular ao mesmo tempo, um ficou
  na sessão 1 (poll a cada ~10 s) e o outro na 2 (abriu com `f0 f0 01 <senha>`,
  leu `02 b0`/`03 e0`), em paralelo.
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
   A nuvem manda a **hora local** (Brasília). Um relay numa máquina em UTC deixa a
   central 3 h adiantada — e os eventos/histórico com hora errada (visto no
   laboratório); o relay tem `--tz` para isso. A central confirma com `f0 fd 00`
   (sessão `00 00 00 00`). Logo após reconectar ela às vezes repete o pedido de
   hora a cada ~5 s por alguns minutos (com o relógio zerado); responder sempre
   resolve. 🟡
4. **Abertura de sessão de controle** (`f0 f0`) ✅ — antes de pedir status ou mandar
   comando, o relay abre a sessão na sessão `00 00 00 0N` enviando o payload **fixo**
   `f0 f0 03 03 06 05 09 00 00 00 01` (o `03 03 06 05 09` é constante em todas as
   capturas; o tail varia entre `00 00 00 01` e `00 00 01 00`). A central confirma
   com `f0 f0 00 <ck>` na sessão `00 0N 00 00`. **Sem essa abertura, a central
   ignora poll e comando.**

   🔑 **Esta sessão NÃO leva o código de acesso** — ele não aparece em texto claro
   em nenhum frame do tráfego de controle. A central **não autentica o servidor**:
   qualquer um que alcance a central e envie esse handshake fixo tem controle total
   (é o que torna o controle local possível, e também a falha de segurança do
   produto). O código de acesso fica exposto, sim, mas no **bloco de config `04 00`
   (usuários)**, não aqui.

   ⚠️ Existe também a variante `f0 f0 01 <dígitos> 10 00`, que abre uma sessão de
   **só leitura**: a central responde status mas dá **NACK (`f0 fd`) em `40 1e`** e
   outros comandos. Use sempre a sessão de controle acima para arme/desarme/choque.
5. **Manter a sessão (e o que NÃO fazer)** ✅ — a sessão de controle se mantém com
   (a) a central mandando `f0 f7` e o servidor respondendo `f0 fe`, e (b) os polls de
   status `0b 4a`. ⚠️ **`f0 f1` é DISCONNECT, não keepalive**: o servidor manda
   `f0 f1` para **encerrar** a sessão de controle (a central confirma com `f0 fe`) e
   depois reabre com `f0 f0` antes do próximo comando. Mandar `f0 f1` "de keepalive"
   **derruba a sessão** — o status continua (não depende dela), mas o comando
   seguinte volta **NACK `0x21`**. Por isso o relay **nunca** manda `f0 f1` e
   **reabre a sessão (`f0 f0`) antes de cada comando**, como o app faz.

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
| `[46..47]` | zonas abertas (bitmap): byte 46 bit0 = zona 1 … bit7 = zona 8 ✅ (ao vivo, 4 sensores) |
| `[54..55]` | zonas disparadas (bitmap, mesma ordem) ✅ (disparo da zona 3 = `04 00`) |
| `[62..63]` | zonas em bypass (bitmap, mesma ordem) ✅ |
| `[72..77]` | relógio: dia mês ano hh mm ss (**binário**, ex.: `10 0b 1a` = 16/11/26) |
| `[153..155]` | versão do módulo (`01 02 0b` = 1.2.11) 🟡 |
| `[157..162]` | MAC da central (o mesmo do registro `3f 94`) ✅ |
| `[163]` | sinal Wi-Fi: RSSI; se `>127`, ler como negativo (`256 - v` = \|dBm\|) 🟡 |

### 4.2 Arme / desarme / choque — comando `40 1e`  ✅
Relay→central: `40 1e <partição> <modo>`.

| Partição | Modo | Efeito |
|---|---|---|
| `01` | `01`/`00` | alarme liga / desliga |
| `02` | `01`/`00` | choque liga / desliga |
| `ff` | `01`/`00` | ambos (partição 255) liga / desliga |

No ELC o 2º byte observado é liga/desliga (`01`/`00`). Armar o alarme (partição 1)
**não** liga o choque (partição 2) — confirmado ao vivo. A resposta da central
varia (`f0 fd 00`, eco `40 1e <p> <m>` ou nada), então **confirme pelo status**
(`[30]`/`[31]`) — é o que o relay faz, reenviando se o estado não mudou. Cada
mudança gera um evento `10 b2` (Contact-ID 407). Em centrais de alarme AMT o
mesmo comando codifica o modo de arme (0=desarma, 1=total, 2=parcial/stay,
3=forçado) — ver §7; não testado no ELC.

### 4.3 Bypass de zona — comando `40 1f`  ✅
Relay→central: `40 1f ff <z1 z2 z3 z4 z5 z6 z7 z8>`, um byte por zona
(`01` = anulada, `00` = normal). O `ff` inicial é o seletor de partição (todas),
igual ao `40 1e`. Ex.: `40 1f ff 00 00 01 00 00 00 00 00` anula só a zona 3.
Confirmado ao vivo pelo relay: o bitmap `[62..63]` vai a `04 00` e volta a `00 00`.
A central responde `f0 fd 00` (ACK) ou eco `40 1f ff 00`.

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
| `02` | fogo — **recusado no ELC** (`f0 fd 21`) ✅ |
| `03` | emergência médica — **recusado no ELC** (`f0 fd 21`) ✅ |

`00` e `01` confirmados ao vivo pelo relay: geram os eventos Contact-ID 122
(silencioso) e 120 (audível) e não deixam alarme/disparo travado no status.

Nosso teste confirmou o `01` (disparo audível, vídeo + mapa3). O `40 1a 00`
apareceu na captura mapa e bate com o tipo "silencioso" (daí não ter efeito
visível). A tabela de tipos foi validada cruzando com a eng. reversa do APK em
`bobaoapae/guardian-api-intelbras` (ver §7). O relay usa `01` por padrão.

### 4.6 Acionar PGM — comando `45 af`  ✅
Relay→central: `45 af <pgm> <estado>`, PGM **base-0** (`00` = PGM1, `01` = PGM2),
estado `01` = liga / `00` = desliga. Ex.: `45 af 00 01` liga a PGM1. A central só
aceita se a PGM estiver no modo "acesso via app" (`03 e0` `[7]`/`[11]` = `01`);
fora dele responde `f0 fd 21` (confirmado ao vivo pelo relay, PGMs em modo `00`).
PGM = saída programável (contato que aciona um aparelho externo: portão, luz…).

### 4.7 Eventos — comando `10 b2`  ✅
Central→relay empurra eventos no padrão **Contact-ID**; o servidor responde `f0 fe`
na sessão `00 00 00 00` (igual à nuvem). É o que gera as notificações. A central às
vezes reenvia o mesmo evento segundos depois (mesmo com o ack, também com a nuvem):
deduplique pelo 1º timestamp.

Layout dos dados (após `10 b2`, 34 bytes) ✅:

| Offset | Campo |
|---|---|
| `[0..5]` | `00 00 00 00 00 01` (fixo nas capturas) |
| `[6]` | `08` |
| `[7]` | qualificador: `01` = evento / abertura, `03` = restauração / fechamento |
| `[8..10]` | código Contact-ID, 1 dígito por byte (**`0a` = 0**): `04 0a 07` = 407 |
| `[11..12]` | partição (`00 01` alarme, `00 02` choque) |
| `[13..15]` | zona ou usuário (`00 00 03` = zona 3) |
| `[16..21]` | data/hora do evento (binário, `DD MM AA hh mm ss`) |
| `[22..27]` | data/hora do envio |

Códigos vistos (todas as capturas):

| Código | Significado | Confiança |
|---|---|---|
| 3 407 / 1 407 | arme / desarme remoto (app, nuvem ou relay); partição 1 alarme, 2 choque | ✅ |
| 3 409 / 1 409 | arme / desarme pelo controle remoto RF (usuário 0) | ✅ |
| 1 130 / 3 130 | disparo / restauração de zona (zona em `[13..15]`) | ✅ |
| 1 120 | pânico audível | ✅ |
| 1 122 | pânico silencioso | ✅ |
| 1 422 / 3 422 | PGM ligada / desligada (partição e zona = nº da PGM) | ✅ |
| 1 306 | programação alterada (após gravar config; visto ao trocar o Wi-Fi pelo app — a ponte de nuvem do HA também rotula assim) | ✅ |
| 1 410 | **fim de sessão remota**: sai ~2 s depois de cada `f0 f1` (app ou relay) | ✅ |
| 3 412 | visto uma vez durante comandos do app; significado em aberto | ⬜ |

O qualificador segue o sentido do Contact-ID: no arme `3` = armou e `1` = desarmou;
na zona `1` = disparou e `3` = restaurou; na PGM `1` = ligou e `3` = desligou.

### 4.8 Recusa de comando — `f0 fd <código>`  ✅
Quando a central **recusa** um comando (`40 1e`, `40 1f`, `45 af`, `40 1a`) ela
responde `f0 fd <código>` ~0,1 s depois, em vez de executar (o status não muda).
Códigos observados:
- **`0x21`** — **comando sem sessão de controle válida**. Principal causa no nosso
  caso: a sessão foi derrubada por um `f0 f1` (ver §3.5) e o comando caiu numa
  sessão fechada. Prova (captura do relay): `f0 f1` em t=10,1 s (central ACK o
  disconnect) → `40 1e` em t=13,1 s → `f0 fd 21`. A nuvem/app nunca manda `f0 f1`
  entre abrir e comandar, então nunca vê `0x21`. O mesmo código aparece na PGM
  (`45 af`) fora do modo "acesso via app" — ou seja, "sem permissão/sessão para
  esta função". **Solução:** não mandar `f0 f1` e reabrir a sessão antes do comando.
  Também é a resposta a **função não suportada/não habilitada**: PGM fora do modo
  app, pânico fogo/médico no ELC (confirmado ao vivo).
- **`0x3f`** — visto no bypass (`40 1f`) recusado.
- **`0x00` NÃO é recusa** ✅ — é o ACK genérico ("ok, sem dados"): a central responde
  `f0 fd 00` a bypass, choque, consultas (`38 5c`, `00 60`, `46 xx`) e à hora, e o
  efeito acontece. (Versões antigas do relay tratavam como recusa e reenviavam.)

Um `f0 fd` de **keepalive** é diferente: o byte final é o checksum válido (xck), não
um código. O relay loga `[RECUSADO] code 0xNN` só em recusa real (≠ `00`) e, para
`40 1e`, confere o resultado no status.

### 4.9 Desligar sirene — comando `40 19`  🟡
Relay→central: `40 19` silencia a sirene sem desarmar (eng. reversa do APK,
`bobaoapae`, ver §7). Ao vivo a central **aceitou** (sem recusa), mas sem alarme
tocando não houve efeito a observar — falta testar com a sirene disparada.

---

## 5. Configuração — leitura/escrita de blocos  ✅

A configuração **não é um protocolo à parte**: é leitura/escrita de blocos de
memória, mesmo enquadramento.

- **Ler**: relay→central `3f 12 <addr:2> <tam:2>` → central responde com os dados.
  Só endereço/tamanho de **início de bloco** devolvem dados próprios; outros
  endereços devolvem `f0 fd 00` ou **espelham** o bloco que os contém (endereços
  baixos → zonas, ≥ `04 00` → usuários). Os dados reais acabam em ~`05 a4`.
- **Gravar**: relay→central `2f 12 <addr:2> <tam:2> <dados:tam>`.

### Mapa de blocos (✅ confirmado por captura)

| Endereço | Tam | Conteúdo |
|---|---|---|
| `00 00` | 128 | **Zonas**: 8 × 16 bytes = `[attr][nome 15 chars]` |
| `02 b0` | 16 | **Nome do eletrificador** |
| `02 c0` | 96 | **Config Wi-Fi**: SSID (32 B) + senha (64 B), padding `ff`, **texto claro** ⚠️; sem IP/DNS (sempre DHCP) |
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

### Gravar config (inclui **trocar a rede Wi-Fi**)  🟡
Todo ajuste de config é um `2f 12 <addr> <tam> <dados>`. Observados em captura
(estrutura confirmada; efeito ao vivo pelo relay ainda não testado):

| Operação | Escrita |
|---|---|
| **Trocar a rede Wi-Fi** | `2f 12 02 c0 00 60 <96 bytes: SSID + senha em texto claro>` — depois a central reconecta na rede nova |
| Renomear zona / mudar atributo | `2f 12 00 00 00 80 <128 bytes: 8×[attr][nome 15]>` |
| Nome do eletrificador | `2f 12 02 b0 00 10 <16 bytes>` |
| Pulsos falhos / modo PGM / reportagem | `2f 12 03 e0 00 20 <32 bytes, offsets acima>` |
| Usuários (nomes/código) | `2f 12 04 00 01 a4 <420 bytes>` ⚠️ contém o código em claro |

> ⚠️ As gravações de `02 c0` (Wi-Fi) e `04 00` (usuários) levam **senha/código em
> texto claro**. O `decode_capture.py` mascara esses blocos; não publique o pcap cru.

---

## 6. Outros opcodes observados (a confirmar)  🟡

Opcodes que aparecem no tráfego servidor→central (app pela nuvem) mas que **não são
necessários** para o controle local e ainda **não foram mapeados a fundo**. Ficam
aqui para completar o mapa. Todos na sessão de app (`00 00 00 0N`).

| Opcode | Bytes (ex.) | Resposta observada | Provável |
|---|---|---|---|
Testados ao vivo pelo relay (só leitura; nada acionou):

| Opcode | Bytes (ex.) | Resposta ao vivo | Conclusão |
|---|---|---|---|
| `3f aa` | `3f aa 00` | **nenhuma** | este firmware não responde (o MAC já vem no status `[157..162]`) |
| `38 5b` | `38 5b` | `38 5b 00` | consulta de flag/estado |
| `38 5c` | `38 5c` | `f0 fd 00` + status | pede atualização de status |
| `0b 01` | `0b 01` | nenhuma clara | inconclusivo |
| `00 60` | `00 60` | `f0 fd 00` + status | pede atualização de status |
| `46 10` | `46 10 ff` | status `0b 4a` | consulta/refresh — não aciona |
| `46 a0` | `46 a0 ff <N>` (N=02/03/04/06) | status / `f0 fd 00` | consulta por partição — não aciona |

> `0b 1a`, listado antes como "buffer de eventos", é quase certamente **falso
> positivo**: `0b 1a` = "11/26" (mês/ano em binário) dentro dos timestamps de
> status/eventos (`10 0b 1a hh mm ss` = 16/11/26 …), não um opcode.

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
