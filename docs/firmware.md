# Firmware do módulo Wi-Fi

Como trocar, na flash do módulo Wi-Fi da central, o endereço do servidor da nuvem por
um endereço seu — a [opção A da instalação](instalacao.md#opção-a--firmware-recomendada).
Inclui a referência técnica do firmware.

> ⚠️ **Segurança física.** A central é um energizador ligado à rede elétrica, com alta
> tensão. Antes de abrir: tire da tomada, desligue a bateria e espere os capacitores
> descarregarem. Há risco de inutilizar o módulo e de perder a garantia.
>
> ⚠️ **Varia entre unidades.** Versão, offsets e até o layout de partições podem mudar
> entre lotes e versões da Intelbras. Trabalhe sempre sobre o dump da **sua** unidade;
> a ferramenta de patch localiza tudo dinamicamente e recusa imagens que não reconhece.
>
> 🔒 **O dump contém segredos.** A partição `nvs` guarda SSID e senha do Wi-Fi e o
> código de acesso. Nunca publique o `.bin` (o `.gitignore` já bloqueia `*.bin`).

## Hardware

O módulo de rede é uma placa removível ("WiFi Connect") encaixada na placa base da
central. Nela ficam o módulo **Espressif ESP-WROOM-02D** (ESP8266), um regulador, um
botão **PROGRAMAR** e um conector 2×5 para a placa base.

O ESP8266 **não tem secure boot nem criptografia de flash**, então a flash pode ser
lida e regravada com `esptool`. O ESP é só a ponte de rede: a lógica de alarme e cerca
fica num microcontrolador da placa base, com o qual o ESP conversa por uma serial
interna (não documentada).

### Ligação para leitura/gravação

Mantenha o módulo na placa "WiFi Connect": ela já faz o *strapping* de boot (`EN`,
`IO15`, `IO0`) e o botão PROGRAMAR é o `IO0`. Bastam 4 fios soldados nos pads do ESP.

```
            [ ANTENA / topo ]
   3V3  1 ┤□                □├ 18  GND
   EN   2 ┤□                □├ 17  IO16
   IO14 3 ┤□                □├ 16  TOUT
   IO12 4 ┤□                □├ 15  RST
   IO13 5 ┤□    (19 GND)    □├ 14  IO5
   IO15 6 ┤□                □├ 13  GND
   IO2  7 ┤□                □├ 12  TXD
   IO0  8 ┤□                □├ 11  RXD
   GND  9 ┤□                □├ 10  IO4
```

Vista de cima, antena no topo (datasheet Espressif ESP-WROOM-02D, seção 2).

| Pad | Sinal | Liga em |
|---|---|---|
| 1 | `3V3` | fonte 3,3 V de **≥ 500 mA** (o pino 3V3 do adaptador não basta) |
| 9 | `GND` | GND comum à fonte e ao adaptador |
| 12 | `TXD` | RX do adaptador |
| 11 | `RXD` | TX do adaptador |

O adaptador USB-serial precisa ser de **lógica 3,3 V**. Se o módulo for removido da
placa, o *strapping* fica por sua conta: `EN`→3V3, `IO15`→GND, `IO2` solto,
`IO0`→GND no boot.

**Modo de gravação:** segure PROGRAMAR e ligue a alimentação com ele pressionado. A
placa não tem auto-reset, então use sempre `--before no-reset --after no-reset`.

## Procedimento

### 1. Backup

```bash
pip install esptool
esptool --port <porta> --before no-reset --after no-reset flash-id
esptool --port <porta> --before no-reset --after no-reset read-flash 0 0x200000 backup1.bin
esptool --port <porta> --before no-reset --after no-reset read-flash 0 0x200000 backup2.bin
```

Os dois arquivos precisam ser idênticos (compare o hash). Leitura não altera nada no
módulo. **Guarde o backup** — é o caminho de volta ao firmware original.

Se aparecer `No serial data received`, confira alimentação, GND comum e solda; se
aparecer `Invalid head of packet`, o módulo bootou o firmware normal — repita a
entrada em modo de gravação. TX/RX invertidos apenas impedem a conexão.

### 2. Gerar a imagem alterada

Escolha um nome de domínio com **até 24 caracteres** (tamanho de
`amt8000.intelbras.com.br`) e use [`tools/patch_server.py`](../tools/patch_server.py):

```bash
python3 tools/patch_server.py backup1.bin patched.bin --novo elc.example.com
```

A ferramenta troca o nome nos dois slots de aplicação, recalcula checksum e SHA256 e
confere a imagem antes e depois. Opções:

| Opção | Efeito |
|---|---|
| `--so-nacional` | troca só `amt8000…` (padrão: também `global.amt8000…`) |
| `--bloquear-ota` | aponta o servidor de atualização para um endereço morto, para uma atualização da Intelbras não desfazer o patch (perde-se as atualizações oficiais) |

Um IP literal também cabe, mas o firmware sempre faz consulta de DNS; prefira um nome.

### 3. Apontar o DNS e regravar

Crie o registro A do nome para o IP interno do relay (ver [instalação](instalacao.md#opção-a--firmware-recomendada)).
Depois, em modo de gravação:

```bash
esptool --port <porta> --before no-reset --after no-reset write-flash \
    --flash-size keep --flash-mode keep --flash-freq keep 0x0 patched.bin
```

Para reverter, grave o `backup1.bin` com o mesmo comando.

Wi-Fi, zonas, sensores e usuários ficam na partição `nvs`, não no código: mudá-los não
exige regravar o firmware.

## Referência técnica

Valores de uma unidade (placa base 1.1.0, módulo 1.2.11).

### Identidade

| Item | Valor |
|---|---|
| Módulo | ESP-WROOM-02D (`-N2`), FCC ID `2ACTZ-ESPWROOM02D` |
| SoC | ESP8266EX, 160 MHz, cristal 26 MHz |
| Flash | 2 MB, SPI DIO, JEDEC `0xA1` / `0x4015` |
| SDK | ESP8266_RTOS_SDK v3.4 (build de 21/10/2025) |
| MAC do rádio | `08:3a:8d:…` (OUI Espressif) |
| MAC do protocolo | `80:85:44:…` (etiqueta, registro `3f 94` e status `[157..162]`) — ID atribuído pela Intelbras, diferente do MAC do rádio |

### Partições (tabela em `0x8000`)

| Partição | Offset | Tamanho | Conteúdo |
|---|---|---|---|
| bootloader | `0x000000` | ~12 KB | 2º estágio |
| `nvs` | `0x009000` | 24 KB | configuração (inclui SSID, senha e código) |
| `otadata` | `0x00f000` | 8 KB | slot ativo |
| `phy_init` | `0x011000` | 4 KB | calibração de RF |
| `ota_0` | `0x012000` | 896 KB | aplicação |
| `ota_1` | `0x112000` | 896 KB | aplicação (segundo slot) |

### Imagem de aplicação

Formato ESP8266 clássico: cabeçalho `0xE9`, 5 segmentos, entry `0x40213f34`. Ao final:

- **checksum** de 1 byte = XOR de todos os bytes de dados dos segmentos com semente
  `0xEF`, no último byte do bloco alinhado em 16;
- **SHA256** de 32 bytes logo depois = `sha256(cabeçalho … byte de checksum)`.

### Endpoints embutidos (texto claro)

| String | Uso |
|---|---|
| `amt8000.intelbras.com.br` | servidor da nuvem (modo nacional) |
| `global.amt8000.intelbras.com.br` | servidor da nuvem (modo global) |
| `amtupdate.intelbras.com.br` / `54.207.162.243` | atualização de firmware (OTA) |

### Strings relevantes

Rede elétrica (`DETECTADO FALHA REDE AC`, `RESTAURADO REDE AC`), bateria de sensores
sem fio (`SENSOR BATERIA DETECTADA/RESTAURADA`), tipos de zona (`ZONA_STAY`,
`ZONA TEMPORIZADA`, `ZONA_INTELIGENTE`), PGM (`PGM1`, `PGM2`) e Wi-Fi (`RSSI_WIFI`).
A bateria da própria central é tratada no microcontrolador da placa base e não aparece
neste firmware.

## Firmware próprio (ESPHome, Tasmota)

Não suportado. Substituir o firmware exige reimplementar a serial interna entre o ESP
e a placa base, que não está documentada; sem ela a central perde a rede. O
procedimento acima mantém o firmware original e muda só o endereço.
