# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões dos Apps do Home Assistant entre parênteses.

## 2026-11-17

### Adicionado
- Alteração do endereço do servidor no firmware do módulo Wi-Fi (ESP8266):
  `tools/patch_server.py` e guia em `docs/firmware.md`. A central passa a conectar no
  relay sem nenhuma configuração de rede.
- `docs/instalacao.md`, reunindo as formas de levar a central até o relay e a
  instalação do relay.
- Referência técnica do firmware (partições, formato de imagem, endpoints).

### Alterado
- Documentação reorganizada: `docs/redirecionamento.md` e `docs/firmware-dump.md`
  incorporados em `instalacao.md` e `firmware.md`.
- Documentada a detecção intermitente de zona aberta com a central desarmada.

## 2026-11-16 — App Local 1.0.1, App Híbrido 0.1.2

### Adicionado
- Eventos `10 b2` decodificados (Contact-ID): arme/desarme, disparo, pânico, PGM,
  programação alterada, fim de sessão.
- Opção `--tz` no relay (hora local enviada à central).
- App Híbrido: opção `inject_session`.

### Corrigido
- `f0 fd 00` passou a ser tratado como confirmação, não como recusa.
- Arme/desarme/choque conferidos pelo status, com reenvio se o estado não mudar.
- Modo híbrido não repassa mais à nuvem as respostas dos comandos locais.

### Confirmado no equipamento
- Controle, status, bypass, pânico, PGM e integração MQTT.
- O endereço do servidor não existe na memória de configuração da central.
- A central alterna entre as portas 9009 e 8080 ao reconectar.

## 2026-11 — App Local 1.0.0, App Híbrido 0.1.0

### Adicionado
- Especificação do protocolo central ⇄ nuvem (`PROTOCOL.md`).
- Relay local com painel web e ponte MQTT para o Home Assistant.
- Apps do Home Assistant (Local e Híbrido).
- Ferramentas de captura e decodificação (`tools/`).
