# Firmware do módulo de rede (ESP8266) — caminhos e limites

Referência para quem quiser ir além do redirecionamento de rede e mexer no próprio
módulo Wi-Fi. **Nada aqui foi testado** — o dump da flash ainda não foi feito. Para o
hardware (chip, marcações, placa), ver [PROTOCOL §1.1](../PROTOCOL.md).

> ⚠️ **Segurança física.** É um energizador de cerca ligado à rede elétrica, com
> alta tensão e capacitores. Antes de abrir: tire da tomada, desligue a bateria e
> espere descarregar. Risco de inutilizar a central e de perder a garantia. É um
> dispositivo de **segurança** — um firmware com bug pode significar o alarme não
> armar ou disparar sozinho.

## O que já está resolvido sem tocar no firmware

O objetivo "controlar local **e** manter o app/nuvem Intelbras funcionando junto" já
é atendido pelo **modo híbrido** do relay (branch `experimental`): a central fala com
o relay, o relay repassa para a nuvem (app segue vivo) e injeta os comandos locais.
Firmware de fábrica intacto. O único "preço" é o redirecionamento na rede
(ver [redirecionamento.md](redirecionamento.md)).

Então mexer no firmware só agrega se o objetivo for **eliminar o redirecionamento**
(trocar a string do endereço) ou **de-Intelbrizar o módulo** (firmware próprio).

## Os três caminhos

| Caminho | Esforço | Ganha | Perde / exige |
|---|---|---|---|
| **1. Relay híbrido** (pronto) | baixo | local + app/nuvem juntos | precisa do redirecionamento na rede |
| **2. Trocar a string do endereço** na flash | médio (abrir, dump, patch) | tira o redirecionamento | acesso físico; firmware fica intacto |
| **3. Firmware próprio** (ESPHome/Tasmota) | alto | módulo 100% seu, sem blob Intelbras | mapear a serial ESP↔placa + reimplementar tudo (inclusive a nuvem, se quiser o app); segurança vira sua responsabilidade |

Não existe "sem limites": ou se aceita o redirecionamento na rede (1), ou se mexe na
flash (2/3). O caminho 3 troca o limite do redirecionamento pelo trabalho e risco de
manter um protocolo de segurança reimplementado por conta própria.

## Caminho 2 — mover só a string do endereço

Mantém todo o firmware original (inclusive a conversa com a placa base); só muda para
onde o módulo conecta. Como o ESP8266 não tem secure boot nem flash encryption, a
imagem alterada é aceita.

1. **Backup primeiro.** A placa Intelbras ("WiFi Connect", módulo ESP-WROOM-02D)
   tem um botão **PROGRAMAR** (= `IO0`) e já faz o strapping de `EN`/`IO15`/`IO0`.
   **Mantendo o módulo na placa**, basta soldar 4 fios nos pads do módulo e usar o
   botão — não precisa mexer em `EN`/`IO15`/`IO2`.

   Pinos do ESP-WROOM-02D (vista de cima, antena no topo; esquerda 1→9 de cima p/
   baixo, direita 10→18 de baixo p/ cima — datasheet Espressif, seção 2):

   ```
               [ ANTENA / topo ]
      3V3  1 ┤□                □├ 18  GND
      EN   2 ┤□                □├ 17  IO16
      IO14 3 ┤□                □├ 16  TOUT
      IO12 4 ┤□                □├ 15  RST
      IO13 5 ┤□    (19 GND)    □├ 14  IO5
      IO15 6 ┤□                □├ 13  GND
      IO2  7 ┤□                □├ 12  TXD → RX do adaptador
      IO0  8 ┤□                □├ 11  RXD → TX do adaptador
      GND  9 ┤□                □├ 10  IO4
   ```

   | Pad | Função | Liga em |
   |---|---|---|
   | 1 (topo esq.) | `3V3` | 3,3 V da fonte |
   | 9 (base esq.) | `GND` | GND comum (fonte + adaptador) |
   | 12 (dir., 3º de baixo) | `TXD` | **RX** do adaptador |
   | 11 (dir., 2º de baixo) | `RXD` | **TX** do adaptador |

   Alimentação: use fonte 3,3 V de **≥500 mA** (o datasheet exige isso), **não** o
   pino 3V3 do adaptador; GND comum; adaptador em **lógica 3,3 V**. O módulo é `-N2`
   = flash de **2 MB**.

   **Modo download:** segure **PROGRAMAR** (`IO0` em nível baixo) e **ligue a
   alimentação** com ele pressionado. A placa não tem auto-reset (DTR/RTS), então:
   ```bash
   pip install esptool
   esptool --port COM? --before no_reset --after no_reset flash_id
   esptool --port COM? --before no_reset --after no_reset read_flash 0 0x200000 dump.bin
   ```
   Se der "Failed to connect", repita a sequência; persistindo, **inverta TXD/RXD**
   (seguro). Leia **duas vezes** e compare — se baterem, o backup é confiável.

   > **Módulo removido da placa (bare):** aí você mesmo faz o strapping — `EN`→3V3,
   > `IO15`→GND, `IO2`→3V3/solto, `IO0`→GND no boot (modo download) — além de
   > `3V3`/`GND`/`TXD`/`RXD`. Mantendo na placa, ignore esses.
2. **Escolha o endereço de destino.** Recomendado: um **nome de domínio** que você
   aponta para o IP do HA na sua LAN (ex.: `elc.seudominio.com → 192.168.31.10`).
   Vantagens: se o IP do HA mudar, você edita só o DNS (sem regravar), e **elimina o
   redirecionamento de DNS no roteador**. Tem que caber em **≤ 24 caracteres** (ver
   abaixo). Um **IP literal** (`192.168.31.10`) também cabe, mas o firmware faz
   resolução de DNS mesmo assim — pode não aceitar IP; teste.

   > **Aponte o nome para o IP INTERNO.** Nada fica exposto na internet: de fora, o
   > nome resolve para um IP privado inalcançável; só a sua LAN conecta. No Cloudflare,
   > use registro **A "DNS only" (nuvem cinza)**, não proxied. **Nunca** aponte para um
   > IP público com port-forward da 9009 — o relay não tem senha nem TLS.

3. **Gere a imagem alterada** com a ferramenta [`tools/patch_server.py`](../tools/patch_server.py),
   que troca as strings de host nos dois slots de OTA e **recalcula o checksum (XOR,
   semente `0xEF`) e o SHA256 anexado** de cada imagem:
   ```bash
   python3 tools/patch_server.py dump.bin dump_patched.bin --novo elc.seudominio.com
   # opcional: --bloquear-ota  (impede que uma atualização da Intelbras reverta o patch)
   ```
   Ela confere o checksum/SHA256 **antes** (aborta se não entender a imagem) e **depois**
   (garante que ficou válida). Fazendo à mão: edite as strings no mesmo offset (novo +
   `00` de terminação, resto preenchido com `00`, sem mover nada); o checksum é o XOR
   de todos os dados dos segmentos com semente `0xEF`, gravado no último byte do bloco
   alinhado em 16; o SHA256 é `sha256(cabeçalho..byte de checksum)` logo após ele.

4. **Aponte o DNS.** No seu provedor (Cloudflare, etc.), crie `elc.seudominio.com`
   como **A → IP do HA**, *DNS only*. Teste de um PC na LAN: `nslookup elc.seudominio.com`
   deve devolver o IP do HA.

5. **Regrave e teste.** Em modo download (segure PROGRAMAR e ligue), grave a imagem
   inteira de volta, **sem alterar o cabeçalho** da flash:
   ```bash
   esptool --port COM? --before no-reset --after no-reset \
     --flash-size keep --flash-mode keep --flash-freq keep \
     write-flash 0x0 dump_patched.bin
   ```
   Religue a central e suba o relay/HA no IP de destino. Se algo der errado, **regrave
   o `dump.bin` original** — por isso guarde-o para sempre.

Depois disso o módulo conecta direto no seu relay/HA, **sem precisar de DNS/DNAT no
roteador**. O app/nuvem da Intelbras para de funcionar (a central fala com o seu HA);
para manter o app, rode o relay em modo híbrido (experimental). **Wi-Fi, sensores,
zonas e usuários são config (ficam na NVS/central, não no firmware)** — mudá-los não
exige regravar; com o app morto, você os gerencia pelo relay ou revertendo o firmware.

### Mapa da flash (ESP8266 RTOS SDK, 2 MB) — confirmado no dump

| Partição | Offset | Tam | Conteúdo |
|---|---|---|---|
| `nvs` | `0x009000` | 24 KB | config (inclui SSID/senha Wi-Fi) |
| `otadata` | `0x00f000` | 8 KB | qual slot (`ota_0`/`ota_1`) está ativo |
| `phy_init` | `0x011000` | 4 KB | calibração de RF |
| `ota_0` | `0x012000` | 896 KB | app slot 0 (host em `~0x7b8e4`) |
| `ota_1` | `0x112000` | 896 KB | app slot 1 (cópia; host em `~0x17b8e4`) |

Hosts embutidos no app (texto claro, sem criptografia):
`amt8000.intelbras.com.br` (modo NACIONAL), `global.amt8000.intelbras.com.br`
(GLOBAL) e `amtupdate.intelbras.com.br` (OTA, com IP fixo `54.207.162.243`). A
ferramenta troca os dois primeiros nos dois slots; `--bloquear-ota` também mata o
terceiro e o IP.

> ⚠️ **Pode variar de uma central para outra.** Offsets, versão de firmware, tamanho
> da flash e até o layout de partições podem mudar entre lotes/versões da Intelbras —
> **não há como garantir**. Sempre trabalhe sobre o **dump da sua própria unidade**;
> a ferramenta localiza as strings e as partições dinamicamente e recusa a imagem se
> o checksum não bater, em vez de assumir offsets fixos.

## Caminho 3 — firmware próprio (ESPHome/Tasmota)

O muro é a **serial interna ESP↔MCU da placa base**: o ESP não controla a central
sozinho, ele conversa com o MCU que faz o alarme/cerca, num protocolo próprio
**diferente** do protocolo ESP↔nuvem deste repo e **ainda não mapeado**. Gravar
ESPHome sem isso deixa a central sem rede (alarme não responde).

Para viabilizar:

1. **Grampear TX/RX** entre o módulo e a placa base com um analisador lógico (ou um
   segundo serial), com a central funcionando normalmente.
2. **Decodificar** o protocolo (enquadramento, comandos de arme/desarme/choque,
   respostas, provável checksum/contador). Anotar a ação no app e casar com os bytes.
3. **Reimplementar** como componente custom (C++) no ESPHome.
4. Para manter o app/nuvem, o firmware (ou o HA) teria de **também** falar o
   protocolo de nuvem de saída — na prática, reconstruir o que o firmware de fábrica
   já faz.

⚠️ Cuidado de pinos: no ESP8266 a serial para a placa pode usar o **mesmo UART**
da gravação/boot log (GPIO1/3). Confirme por qual par de pinos a placa conversa antes
de planejar logs e gravação.

## O que o dump revelou

Resumo abaixo; especificações completas (identidade, SDK/build, partições, estrutura
da imagem, strings) em **[docs/firmware-dump.md](firmware-dump.md)**.

- **Chip/SDK:** ESP8266EX, **ESP8266 RTOS SDK v3.4**, flash 2 MB, dual-OTA + NVS (mapa acima).
- **Servidor em texto claro**, sem criptografia nem secure boot → editável.
- **Integridade** 100% reproduzível: checksum XOR (semente `0xEF`) + SHA256 anexado.
- **Eventos confirmados no firmware:** falta/retorno de **rede AC**
  (`DETECTADO FALHA REDE AC` / `RESTAURADO REDE AC`) e **bateria de sensor**
  (`SENSOR BATERIA DETECTADA/RESTAURADA`) — mapeáveis como eventos/sensores no HA.
- **Limite:** o ESP é só a ponte Wi-Fi. Bateria interna do painel, disparo e lógica de
  alarme ficam no **MCU da placa base**, fora deste dump — o firmware não traz um campo
  de "bateria do painel"; isso se mapeia por captura (evento `10 b2` de bateria baixa)
  ou por um bit de "problema" no status.

## Situação atual

- Dump da flash: **feito e analisado**; patch de endereço (`patch_server.py`)
  **validado ao vivo em 2026-11-17**: com o firmware apontando para um nome DNS próprio
  (→ IP do HA), a central conecta direto no relay **sem redirecionamento no roteador**.
  O app/nuvem da Intelbras deixa de funcionar (controle 100% local).
- Serial ESP↔placa: **não mapeada** (é o que trava o caminho 3).
- Recomendação prática: para "local + nuvem juntos", use o **modo híbrido** (pronto);
  para tirar o redirecionamento de vez, o **caminho 2** (patch do endereço) é o de
  menor risco.

Se a central for aberta para o caminho 2, aproveite para já grampear a serial interna
(caminho 3) e capturar alguns comandos — isso define se o firmware próprio é viável.
