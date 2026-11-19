# Protocolo ELC 6012 NET

Protocolo que o eletrificador **Intelbras ELC 6012 NET** usa para falar com a nuvem
Intelbras: TCP na porta 9009, em texto claro, sem TLS. Obtido por captura de rede do
próprio equipamento, partindo do trabalho de
[rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net). A implementação de
referência do lado servidor está em [`relay/`](relay/).

Referência: placa base 1.1.0, módulo Wi-Fi 1.2.11. Outras versões podem diferir.

> ✅ confirmado · 🟡 parcial ou inferido · ⬜ não mapeado. MACs dos exemplos são fictícios.

---

## 1. Arquitetura

A central mantém uma conexão TCP **de saída, permanente**, com o relay. O app
(ou um cliente) conecta no mesmo relay e é roteado até a central pelo MAC. Na LAN
a central só responde a sondas de descoberta na porta 9009 (segundo o projeto
rhacius); **todo o controle passa pelo relay**.

| Servidor | Papel |
|---|---|
| `amt8000.intelbras.com.br` | relay onde a central conecta (modo nacional; ex.: `52.67.212.35`) |
| `global.amt8000.intelbras.com.br` | relay do modo global (presente no firmware) |
| `amt.intelbras.com.br` | usado pelo app para descobrir em qual relay a central está |
| `amtupdate.intelbras.com.br` | atualização de firmware do módulo (OTA) |

O nome `amt8000.intelbras.com.br` é **fixo no firmware do módulo Wi-Fi** ✅ — não
existe na memória de configuração da central nem há comando para alterá-lo. Para usar
um servidor local é preciso desviar a conexão na rede ou alterar o firmware (ver
[docs/instalacao.md](docs/instalacao.md) e [docs/firmware.md](docs/firmware.md)).

**Portas e reconexão** ✅ — a central conecta na porta **9009**; se a conexão falhar,
alterna entre **9009 e 8080** a cada ~11 s (a nuvem atende nas duas) e refaz a
consulta de DNS a cada ciclo.

**Autenticação** ✅ — a central se registra enviando MAC e modelo e aceita o servidor
que responder; não há TLS, token ou desafio. Por isso um servidor local funciona, e
por isso ele deve ficar restrito à rede local.

### 1.1 Módulo de rede

A conexão é feita por um módulo **ESP-WROOM-02D (ESP8266)** numa placa removível; a
lógica de alarme e cerca fica num microcontrolador da placa base. Hardware, flash e
como alterar o endereço do servidor: [docs/firmware.md](docs/firmware.md).

---

## 2. Enquadramento

Frames de controle:

```
[sessão : 4 bytes][tam : 2 bytes BE][payload : tam bytes][checksum : 1 byte]
total = 7 + tam     checksum = XOR(todos os bytes anteriores) ^ 0xFF
```

- `sessão` = **índice da sessão de app**, não um contador por mensagem. ✅ Vale
  `00 00 00 00` na conexão base (registro, hora, tiques `f0 fe`) e `00 00 00 0N`
  durante a sessão de app N. A nuvem atribui **um índice por cliente conectado**
  (dois clientes simultâneos usam as sessões 1 e 2 em paralelo).
  Dentro de uma sessão o índice é **fixo**: `f0 f0`, `0b 4a`, `40 1e`, `f0 f1`
  todos usam o mesmo `00 00 00 0N`. A central ecoa com os dois primeiros bytes
  trocados (`00 00 00 01` do servidor ⇄ `00 01 00 00` da central).
- **Exceção — resposta de status (`0b 4a`):** o campo `tam` vale o total (164) e
  **não há checksum** nesta versão. Outras versões enviam 165 bytes com checksum 🟡
  (segundo o projeto rhacius).
- **Checksum só nos frames que o servidor envia.** ✅ O XOR^0xFF
  acima vale para servidor → central; nos frames que a **central** manda ele **não
  bate** (ex.: `f0 fe` vem com `f1`, mas o XOR^0xFF daria `f2`), e o status 164B
  nem tem checksum. Por isso o servidor **não deve validar** o checksum recebido.
- **Enquadramento por re-sincronização.** ✅ A central às vezes manda `f0 fd`/`f0 fe`
  com um byte `00` a mais, mas mantém o campo `tam`=`00 02` — então `7+tam`
  consome 1 byte a menos. Como o checksum não serve de âncora, o servidor valida o
  **cabeçalho** de cada frame (`00 0N 00 00` + comando conhecido) e, se o próximo
  byte não for um cabeçalho válido, descarta-o e realinha. Um `f0 fd`/`f0 fe`
  fica no máximo 1 byte torto (é só ack), e status/eventos/comandos voltam a cair
  certos.

Exemplos reais (✅):

| Frame | Bytes |
|---|---|
| ack ok | `00 00 00 00 00 02 f0 fe f3` |
| poll de status | `00 00 00 01 00 02 0b 4a bd` |
| comando choque ON | `00 00 00 01 00 04 40 1e 02 01 a7` |

---

## 3. Sessão (central ⇄ servidor)

Sequência ao conectar ✅:

1. **Registro** — a central envia `3f 94 45 00 00 <MAC:6> <modelo> 01 01 …`; o
   servidor responde `f0 fe`.
2. **Keepalive** — a central envia `f0 f7`; o servidor responde `f0 fe`.
3. **Hora** — a central pede `f0 80 03`; o servidor responde
   `f0 80 <AA MM DD DS hh mm ss>` em **BCD** (DS = dia da semana), ex.:
   `26 11 13 06 08 18 04`. A central confirma com `f0 fd 00`. A nuvem envia a **hora
   local** (Brasília); um servidor em UTC deixa eventos e histórico com a hora errada.
   Logo após reconectar, a central pode repetir o pedido a cada ~5 s por alguns
   minutos 🟡; basta responder sempre.
4. **Abertura da sessão de controle** (`f0 f0`) — antes de ler status ou enviar
   comandos, o servidor envia na sessão `00 00 00 0N` o payload fixo
   `f0 f0 03 03 06 05 09 00 00 00 01` (o mesmo usado pela nuvem). A central confirma
   com `f0 f0 00 <ck>` na sessão `00 0N 00 00`. Sem essa abertura, a central ignora
   leituras e comandos.

   O byte após `f0 f0` na resposta é o resultado: `00` = controle liberado. Com `01`,
   o status funciona mas todo comando é recusado com `0x21` ✅. Isso acontece quando a
   central reconecta **sem reiniciar** e a sessão da conexão anterior não foi encerrada
   (o relay caiu, a conexão foi resetada): a sessão antiga continua presa. Encerrar com
   `f0 f1` na mesma sessão e reabrir com `f0 f0` devolve `00` ✅. Por isso o relay
   encerra a sessão (`f0 f1`) ao parar e, se receber código diferente de `00`, faz
   `f0 f1` + `f0 f0` uma vez por conexão.

   A abertura não leva o código de acesso (ele fica no bloco de usuários `04 00`, §5).
   A variante `f0 f0 01 <dígitos> 10 00` abre uma sessão **somente leitura**: status
   funciona, comandos recebem recusa (`f0 fd`).
5. **Manutenção** — a sessão se mantém com o keepalive da central (`f0 f7` → `f0 fe`)
   e com as leituras de status. **`f0 f1` encerra a sessão** (não é keepalive):
   depois dele, comandos recebem recusa `0x21` até uma nova abertura. Durante o uso,
   não envie `f0 f1`; reabra a sessão (`f0 f0`) antes de cada comando, como faz o app,
   e espere a confirmação antes de mandar o comando. Envie `f0 f1` só para encerrar
   (ao parar o servidor) ou para liberar uma sessão presa (item 4).

---

## 4. Controle e monitoração

### 4.1 Status — comando `0b 4a`  ✅
Servidor envia `00 00 00 01 00 02 0b 4a bd`; a central responde **164 bytes**.
Offsets a partir do byte 0 do frame:

| Offset | Campo |
|---|---|
| `[8]` | modelo (`0x35` = ELC 6012 NET) |
| `[30]` bit0 | choque ligado |
| `[31]` bit0 | alarme armado |
| `[46..47]` | zonas abertas (bitmap): byte 46 bit0 = zona 1 … bit7 = zona 8 ✅ — ver nota abaixo |
| `[54..55]` | zonas disparadas (bitmap, mesma ordem; zona 3 = `04 00`) ✅ |
| `[62..63]` | zonas em bypass (bitmap, mesma ordem) ✅ |
| `[72..77]` | relógio: dia mês ano hh mm ss (**binário**, ex.: `10 0b 1a` = 16/11/26) ✅ |
| `[152]` | muda junto com o dia do mês (`[72]`) — contador/índice? 🟡 |
| `[153..155]` | versão do módulo (`01 02 0b` = 1.2.11) 🟡 |
| `[157..162]` | MAC da central (o mesmo do registro `3f 94`) ✅ |
| `[163]` | sinal Wi-Fi: RSSI; se `>127`, ler como negativo (`256 - v` = \|dBm\|) 🟡 |

**Zonas abertas com a central desarmada:** a atualização de `[46..47]` é intermitente —
aberturas curtas ou em certas zonas podem não aparecer (o app oficial se comporta igual).
Com o alarme armado, a abertura gera disparo (`[54..55]` e evento `10 b2`) imediatamente.

### 4.2 Arme / desarme / choque — comando `40 1e`  ✅
Servidor → central: `40 1e <partição> <modo>`.

| Partição | Modo | Efeito |
|---|---|---|
| `01` | `01`/`00` | alarme liga / desliga |
| `02` | `01`/`00` | choque liga / desliga |
| `ff` | `01`/`00` | ambos (partição 255) liga / desliga |

Armar o alarme (partição 1) não liga o choque (partição 2). A resposta da central
varia (`f0 fd 00`, eco `40 1e <p> <m>` ou nenhuma), então **confirme pelo status**
(`[30]`/`[31]`). Cada mudança gera um evento `10 b2` (Contact-ID 407). Nas centrais
de alarme AMT o segundo byte codifica o modo de arme (0 desarma, 1 total, 2 parcial,
3 forçado) — no ELC só `00`/`01` foram observados.

### 4.3 Bypass de zona — comando `40 1f`  ✅
Servidor → central: `40 1f ff <z1 z2 z3 z4 z5 z6 z7 z8>`, um byte por zona
(`01` = anulada, `00` = normal). O `ff` inicial é o seletor de partição (todas),
igual ao `40 1e`. Ex.: `40 1f ff 00 00 01 00 00 00 00 00` anula só a zona 3.
O bitmap `[62..63]` reflete a mudança. A central responde `f0 fd 00` (ACK) ou eco
`40 1f ff 00`.

### 4.4 Histórico de eventos — comando `39 00`  ✅
Servidor → central: `39 00 <página 0..7>`; a central responde com a página de eventos,
cada registro com 15 bytes = código Contact-ID (9B) + timestamp `DD MM YY HH MM SS`.

### 4.5 Pânico — comando `40 1a`  ✅
Servidor → central: `40 1a <tipo>`:

| Tipo | Efeito |
|---|---|
| `00` | pânico **silencioso** (sem sirene; alerta ao monitoramento) |
| `01` | pânico **audível** (dispara a sirene) |
| `02` | fogo — **recusado no ELC** (`f0 fd 21`) ✅ |
| `03` | emergência médica — **recusado no ELC** (`f0 fd 21`) ✅ |

`00` e `01` geram os eventos Contact-ID 122 e 120 e não deixam alarme ou disparo
travados no status. Os tipos coincidem com os do app (§7).

### 4.6 Acionar PGM — comando `45 af`  ✅
Servidor → central: `45 af <pgm> <estado>`, PGM **base-0** (`00` = PGM1, `01` = PGM2),
estado `01` = liga / `00` = desliga. Ex.: `45 af 00 01` liga a PGM1. A central só
aceita se a PGM estiver no modo "acesso via app" (`03 e0` `[7]`/`[11]` = `01`);
fora dele responde `f0 fd 21`. PGM é uma saída programável (contato para acionar um
equipamento externo).

### 4.7 Eventos — comando `10 b2`  ✅
A central envia eventos no padrão **Contact-ID**; o servidor responde `f0 fe` na sessão
`00 00 00 00`. São a base das notificações. A central às vezes reenvia o mesmo evento
segundos depois, mesmo com o ack: deduplique pelo primeiro timestamp.

Layout dos dados (após `10 b2`, 34 bytes) ✅:

| Offset | Campo |
|---|---|
| `[0..5]` | `00 00 00 00 00 01` (constante) |
| `[6]` | `08` |
| `[7]` | qualificador: `01` = evento / abertura, `03` = restauração / fechamento |
| `[8..10]` | código Contact-ID, 1 dígito por byte (**`0a` = 0**): `04 0a 07` = 407 |
| `[11..12]` | partição (`00 01` alarme, `00 02` choque) |
| `[13..15]` | zona ou usuário (`00 00 03` = zona 3) |
| `[16..21]` | data/hora do evento (binário, `DD MM AA hh mm ss`) |
| `[22..27]` | data/hora do envio |

Códigos observados:

| Código | Significado | Confiança |
|---|---|---|
| 3 407 / 1 407 | arme / desarme remoto; partição 1 alarme, 2 choque | ✅ |
| 3 409 / 1 409 | arme / desarme pelo controle remoto RF (usuário 0) | ✅ |
| 1 130 / 3 130 | disparo / restauração de zona (zona em `[13..15]`) | ✅ |
| 1 120 | pânico audível | ✅ |
| 1 122 | pânico silencioso | ✅ |
| 1 422 / 3 422 | PGM ligada / desligada (partição e zona = nº da PGM) | ✅ |
| 1 306 | programação alterada (após gravar configuração) | ✅ |
| 1 410 | fim de sessão remota (~2 s após um `f0 f1`) | ✅ |
| 3 412 | desconhecido (visto uma vez, durante comandos do app) | ⬜ |

O qualificador segue o sentido do Contact-ID: no arme `3` = armou e `1` = desarmou;
na zona `1` = disparou e `3` = restaurou; na PGM `1` = ligou e `3` = desligou.

### 4.8 Resposta `f0 fd <código>`  ✅
Após um comando, a central pode responder `f0 fd <código>` em ~0,1 s:

| Código | Significado |
|---|---|
| `00` | **ACK** genérico — o comando foi aceito (bypass, choque, consultas, hora) |
| `21` | recusa: sem sessão de controle aberta (ex.: após `f0 f1`) ou função não permitida (PGM fora do modo app, pânico fogo/médico) |
| `3f` | recusa observada no bypass |

Em recusa o status não muda. Um `f0 fd` cujo último byte é o próprio checksum do frame
é keepalive, não resposta a comando.

### 4.9 Desligar sirene — comando `40 19`  🟡
Servidor → central: `40 19` silencia a sirene sem desarmar (comando conhecido pelo app,
§7). A central aceita o comando; o efeito com a sirene tocando não foi verificado.

---

## 5. Configuração — leitura/escrita de blocos  ✅

A configuração é lida e gravada em blocos de memória, com o mesmo enquadramento.

- **Ler**: servidor → central `3f 12 <addr:2> <tam:2>`; a central responde com os dados.
  Só endereço/tamanho de **início de bloco** devolvem dados próprios; outros
  endereços devolvem `f0 fd 00` ou **espelham** o bloco que os contém (endereços
  baixos → zonas, ≥ `04 00` → usuários). Os dados reais acabam em ~`05 a4`.
- **Gravar**: servidor → central `2f 12 <addr:2> <tam:2> <dados:tam>`.

### Mapa de blocos  ✅

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

### Gravação  🟡
Todo ajuste é um `2f 12 <addr> <tam> <dados>`. Formatos observados no tráfego do app
(não executados pelo relay):

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

## 6. Outros opcodes  🟡

Opcodes enviados pelo app que não são necessários para o controle local. Testados como
consulta (nenhum aciona nada):

| Opcode | Exemplo | Resposta | Interpretação |
|---|---|---|---|
| `3f aa` | `3f aa 00` | nenhuma | pedido de MAC; não suportado nesta versão (o MAC vem no status) |
| `38 5b` | `38 5b` | `38 5b 00` | consulta de estado |
| `38 5c` | `38 5c` | `f0 fd 00` + status | pede atualização de status |
| `0b 01` | `0b 01` | — | inconclusivo |
| `00 60` | `00 60` | `f0 fd 00` + status | pede atualização de status |
| `46 10` | `46 10 ff` | status | consulta |
| `46 a0` | `46 a0 ff <N>` | status / `f0 fd 00` | consulta por partição |

---

## 7. Referências

- **[rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net)** — mapeamento
  do protocolo app ⇄ nuvem e integração via nuvem para o ELC 6012 NET; base deste
  trabalho.
- **[bobaoapae/guardian-api-intelbras](https://github.com/bobaoapae/guardian-api-intelbras)**
  (MIT) — cliente da nuvem Intelbras a partir do app. Os opcodes coincidem (`40 1e`,
  `0b 4a`, `40 1a`, `40 1f`, `45 af`, `f0 f0`, `40 19`), assim como o checksum
  XOR^0xFF e os tipos de pânico.

Este projeto documenta o **lado servidor**: o que a central espera da nuvem
(enquadramento, abertura de sessão, keepalive, status sem checksum, blocos de
configuração), verificado contra capturas do ELC 6012 NET.
