# ELC 6012 NET Local

Controla o eletrificador **Intelbras ELC 6012 NET** 100% pela sua rede, **sem a
nuvem da Intelbras e sem internet**. A central conecta neste App (no lugar da
nuvem) e as entidades aparecem sozinhas no Home Assistant via MQTT Discovery:

- `switch` **Cerca** (choque liga/desliga)
- `alarm_control_panel` **Alarme** (armar/desarmar; mostra "disparado")
- `binary_sensor` **Disparo** e **Zona 1…8**

Controle confirmado ao vivo (arme/desarme/choque/tudo). Projeto:
https://github.com/wesleycp4/elc6012net-local

## Antes de iniciar

1. **App Mosquitto** instalado e rodando (as credenciais vêm sozinhas).
2. **Redirecione a central para o HA.** A central procura o servidor
   `amt8000.intelbras.com.br` na porta 9009. Faça esse nome apontar para o IP do
   seu Home Assistant no DNS da sua rede (roteador, AdGuard, Pi-hole…), por
   exemplo: `amt8000.intelbras.com.br → 192.168.31.10`. Depois desligue e religue a
   central para ela reconectar.
3. **Pare o App de nuvem "ELC 6012 NET"**: com a central falando com este App, a
   nuvem não a enxerga mais.
4. **Só um App por vez** na porta 9009 — não rode junto com o "Híbrido".

## O que esperar

- Com a central conectada, o dispositivo fica **online** no HA; se ela cair, fica
  **indisponível** e volta sozinho quando reconectar.
- **O app oficial da Intelbras para de funcionar** neste modo (a central não fala
  mais com a nuvem). Para manter o app/avisos da Intelbras, veja o App Híbrido.
- As zonas seguem o bit do status (a do sensor da porta da cozinha apareceu como
  zona 5). Renomeie as entidades conforme a sua fiação.

## Opções

| Opção | Padrão | Para quê |
|---|---|---|
| `poll` | 5 | Intervalo (s) da consulta de status |
| `node` | `elc6012_local` | ID do dispositivo no MQTT/HA |
| `name` | `ELC 6012 NET (local)` | Nome do dispositivo no HA |

## Segurança

O App aciona uma **cerca elétrica**. Quem publicar nos tópicos de comando do MQTT
consegue ligá-la — mantenha o broker com usuário/senha (o padrão do Mosquitto).
