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
2. **Ache a string** `amt8000.intelbras.com.br` (e veja se há `amt.intelbras.com.br`):
   ```bash
   grep -abo "amt8000.intelbras.com.br" dump.bin
   ```
3. **Troque pelo seu endereço**, do **mesmo tamanho ou menor**, completando o resto
   com `00` (não mova nada de lugar). Ex.: um host curto de DuckDNS apontando para o
   HA, ou o IP do HA se o firmware aceitar IP. Edite no mesmo offset, sem inserir nem
   remover bytes.
4. **Recalcule o checksum/hash da imagem.** O formato de imagem do ESP8266 tem um
   checksum (e, conforme o build, um hash). Reempacote com `esptool elf2image` não se
   aplica (não temos o ELF); edite a imagem e corrija o checksum do segmento, ou use
   uma ferramenta que recalcule. **Este é o passo incerto** — validar relendo.
5. **Regrave e teste:**
   ```bash
   esptool.py write_flash 0 dump_patched.bin
   ```
   Se não subir, regrave o `dump.bin` original.

Depois disso o módulo conecta direto no seu relay/HA, sem precisar de DNS nem DNAT.
Uma atualização OTA da Intelbras desfaz a alteração.

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

## Situação atual

- Dump da flash: **não feito**.
- Serial ESP↔placa: **não mapeada** (é o que trava o caminho 3).
- Recomendação prática: para "local + nuvem juntos", use o **modo híbrido** (pronto);
  para tirar o redirecionamento, o **caminho 2** é o de menor risco.

Se um dia a central for aberta para o caminho 2, aproveite para já grampear a serial
interna (caminho 3) e capturar alguns comandos — isso define se o firmware próprio é
viável.
