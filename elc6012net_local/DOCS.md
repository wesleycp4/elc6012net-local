# ELC 6012 NET Local

Controla o eletrificador **Intelbras ELC 6012 NET** pela rede local, sem a nuvem da
Intelbras e sem internet. A central conecta neste App no lugar da nuvem, e as
entidades aparecem sozinhas no Home Assistant via MQTT:

- `alarm_control_panel` **Alarme** — armar / desarmar
- `switch` **Cerca** — choque liga / desliga
- `binary_sensor` **Disparo** e **Zona 1…8**
- `sensor` **Sinal Wi-Fi** — dBm (diagnóstico)

Projeto e documentação completa: https://github.com/wesleycp4/elc6012net-local

## Antes de iniciar

1. Tenha o **App Mosquitto** rodando (as credenciais do MQTT vêm automaticamente).
2. Faça a central conectar no IP deste Home Assistant, porta 9009 — alterando o
   firmware do módulo Wi-Fi ou redirecionando `amt8000.intelbras.com.br` na rede:
   https://github.com/wesleycp4/elc6012net-local/blob/main/docs/instalacao.md
3. Pare outras integrações da central (ex.: o App de nuvem) e não rode junto com o
   App Híbrido — os dois usam a porta 9009.
4. Confira que **Iniciar no boot** e **Watchdog** estão ativos (padrão desde a 1.1.0): sem o App, a central fica sem servidor.

## Funcionamento

- Com a central conectada, o dispositivo fica disponível; se ela desconectar, as
  entidades ficam indisponíveis e voltam sozinhas na reconexão.
- O app oficial e as notificações da Intelbras não funcionam neste modo.
- As zonas seguem a numeração da central; renomeie as entidades como preferir.
- Com a central desarmada, a detecção de zona aberta é intermitente. Armada, a
  abertura gera disparo imediato.
- A hora enviada à central usa o fuso do Home Assistant.
- Depois de uma reconexão, a central pode manter presa a sessão anterior; o App
  detecta (`f0 f0 01` no log) e libera sozinho. Se o log disser que continua sem
  controle, desligue e religue a central.

## Opções

| Opção | Padrão | Descrição |
|---|---|---|
| `poll` | `5` | intervalo de leitura do status, em segundos |
| `node` | `elc6012_local` | id do dispositivo no MQTT/HA |
| `name` | `ELC 6012 NET (local)` | nome do dispositivo |

## Segurança

O App aciona uma cerca elétrica e não tem autenticação própria: quem alcança a porta
9009 ou publica nos tópicos de comando do MQTT controla a central. Mantenha o broker
com usuário e senha e não exponha a porta 9009 à internet.
