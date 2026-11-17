# Especificações do firmware do módulo Wi-Fi (dump)

Referência técnica do firmware do módulo de rede da central **Intelbras ELC 6012 NET**,
extraída de um dump de flash de **uma** unidade. Serve para consulta por quem for
mexer no módulo (ver o guia de patch em [firmware.md](firmware.md)).

> ⚠️ **Pode variar entre unidades.** Versão, datas, offsets, tamanho de flash e até o
> layout de partições podem mudar entre lotes/versões da Intelbras. **Trabalhe sempre
> sobre o dump da sua própria unidade.** Os números abaixo são de uma amostra, não uma
> garantia.
>
> 🔒 **O dump cru contém segredos** (a partição `nvs` guarda SSID/senha do Wi-Fi e o
> código de acesso). **Nunca** publique o `.bin`; o `.gitignore` bloqueia `*.bin`.
> Este documento traz só estrutura — nenhum segredo.

## Identidade

| Item | Valor |
|---|---|
| Módulo | Espressif **ESP-WROOM-02D** (`-N2`) |
| SoC | **ESP8266EX**, Tensilica L106 @160 MHz |
| Cristal | 26 MHz |
| Flash | **2 MB** (SPI, modo DIO); JEDEC manufacturer `0xA1`, device `0x4015` |
| MAC rádio Wi-Fi (L2) | `08:3a:8d:xx:xx:xx` (OUI Espressif) |
| MAC do protocolo (etiqueta / `3f 94` / status `[157..162]`) | `80:85:44:xx:xx:xx` (ID de conta/placa) |

Os dois MACs são diferentes: o da etiqueta é um ID atribuído pela Intelbras, não o MAC
do rádio.

## Build e SDK

| Item | Valor |
|---|---|
| SDK | **ESP8266_RTOS_SDK v3.4** (FreeRTOS, ESP-IDF-like) |
| Data de build (amostra) | **Oct 21 2025, 10:18:32** |
| PHY lib | Feb 17 2022, commit `14a6402` |
| Componentes presentes | `nvs_flash`, `app_update` (OTA), `spi_flash`, `lwip`, `wpa_supplicant`, `vfs`, `pthread`, `esp_event` |
| Caminho de build original | `C:/ESP_8266/ESP8266_RTOS_SDK/...` |

Implicação: config (Wi-Fi etc.) fica na **NVS**, não no código — mudá-la não exige
regravar o firmware. OTA é o mecanismo `esp_ota` padrão do SDK (dois slots).

## Mapa da flash (tabela de partições @ `0x8000`)

| Partição | Tipo/subtipo | Offset | Tamanho | Conteúdo |
|---|---|---|---|---|
| `nvs` | data/nvs | `0x009000` | 24 KB | **config (SSID/senha Wi-Fi, código) — sensível** |
| `otadata` | data/ota | `0x00f000` | 8 KB | qual slot está ativo |
| `phy_init` | data/phy | `0x011000` | 4 KB | calibração de RF |
| `ota_0` | app/ota_0 | `0x012000` | 896 KB | aplicação (slot 0) |
| `ota_1` | app/ota_1 | `0x112000` | 896 KB | aplicação (slot 1, cópia) |
| bootloader | — | `0x000000` | ~12 KB | 2º estágio (entry `0x40100324`) |

## Estrutura e integridade da imagem de app

Cada imagem de app (`ota_0`/`ota_1`) é um formato ESP8266 clássico:

- Cabeçalho `0xE9`, **5 segmentos** (2× irom0.text/XIP em `0x402xxxxx`, DRAM, 2× IRAM),
  entry `0x40213f34`, modo de flash DIO.
- **Checksum de 8 bits** = XOR de todos os bytes de dados dos segmentos, semente
  `0xEF`, no último byte do bloco alinhado em 16.
- **SHA256** (32 bytes) logo após o checksum = `sha256(cabeçalho .. byte de checksum)`.

Ambos foram reproduzidos byte a byte (ver [`tools/patch_server.py`](../tools/patch_server.py),
que recalcula os dois ao editar). O bootloader do ESP8266 não verifica o SHA256 no
boot (isso é do ESP32), mas a ferramenta corrige mesmo assim para a imagem ficar válida.

## Endpoints de rede (strings em texto claro)

| String | Uso |
|---|---|
| `amt8000.intelbras.com.br` | servidor da nuvem — modo **NACIONAL** (o usado nas capturas) |
| `global.amt8000.intelbras.com.br` | servidor da nuvem — modo **GLOBAL** |
| `amtupdate.intelbras.com.br` | servidor de **atualização OTA** |
| `54.207.162.243` | IP fixo (fallback) do `amtupdate` |

Porta de controle: **9009** (alterna com 8080 na falha — ver [PROTOCOL.md](../PROTOCOL.md)).
Trocar o endereço do servidor = editar as duas primeiras strings (ver [firmware.md](firmware.md)).

## Strings de comportamento (pistas de lógica)

Logs/rótulos que revelam o que o módulo faz (não há offsets de protocolo aqui, mas
ajudam a entender eventos e config):

- **Rede AC / bateria:** `DETECTADO FALHA REDE AC`, `RESTAURADO REDE AC`,
  `SENSOR COMUNICOU COM BATERIA OK`, `SENSOR BATERIA DETECTADA/RESTAURADA`.
- **Zonas:** `ZONA_STAY`, `ZONA TEMPORIZADA`, `ZONA_INTELIGENTE`, `ANALISA_ZONA`,
  `Ativa alarme via Auto_arme`, `Rearme automatico`.
- **Config/menu:** `Nome das zonas`, `Rede WiFi`, `MAC Address`, `RSSI_WIFI = %d`,
  `Current fw version`, `Cloud fw version`.
- **PGM:** `pgm on`, `pgm off`, `PGM1`, `PGM2`.

A bateria interna do painel, disparo e a lógica de alarme ficam no **MCU da placa
base**, que não está neste dump — o ESP é só a ponte Wi-Fi.

## Como foi obtido (e reproduzir)

Módulo na própria placa, 4 fios no ESP (3V3/GND/TXD/RXD) + botão PROGRAMAR para o modo
download; `esptool read_flash 0 0x200000`, lido duas vezes e comparado. Passo a passo e
pinagem em [firmware.md](firmware.md).
