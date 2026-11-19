# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões dos Apps do Home Assistant entre parênteses.

## 2026-11-19 — App Local 1.0.4, App Híbrido 0.1.5

### Corrigido
- **Causa real da recusa `0x21`** (choque não ligava pelo HA): depois de uma reconexão
  sem a central reiniciar, a resposta da abertura de sessão vinha `f0 f0 01` — a
  sessão da conexão anterior ficava presa e a nova só lia status. Agora o relay
  encerra a sessão com `f0 f1` ao parar e, ao receber código diferente de `00`,
  encerra e reabre a sessão uma vez por conexão.

## 2026-11-19 — App Local 1.0.3, App Híbrido 0.1.4

### Corrigido
- O comando passa a ser enviado só depois de a central confirmar a reabertura da
  sessão (`f0 f0`), com até 3 s de espera, em vez de uma pausa fixa de 150 ms.

### Adicionado
- Log do frame bruto nas recusas e do código de resposta da abertura de sessão.

## 2026-11-18 — App Local 1.0.2, App Híbrido 0.1.3

### Corrigido
- Queda da conexão com a central não era detectada: o relay seguia como conectado, o
  HA mostrava o último estado e um comando seguinte derrubava a thread com
  `BrokenPipeError`. Agora qualquer falha de envio/recepção, ou 60 s sem dados da
  central, encerra a conexão e marca o dispositivo como indisponível até a central
  reconectar.
- Arme/desarme/choque para o estado em que a central já está não é mais enviado (a
  central recusava com `0x21` e o relay reenviava duas vezes).
- Recusa `0x21` em arme/desarme/choque passa a ser conferida pelo status, sem
  reenvio duplicado.

### Adicionado
- Horário em cada linha do log.

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
