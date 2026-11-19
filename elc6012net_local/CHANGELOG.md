# Changelog

## 1.1.0

- Código do relay incluído no App (antes era baixado da branch `main` na hora da
  montagem; agora cada versão do App corresponde a um código fixo).
- Novo sensor **Sinal Wi-Fi** (dBm, diagnóstico).
- Alarme mostra só **Armar** (ausente): a central tem um único modo de arme.
- Inicia no boot por padrão e o Supervisor vigia a porta 9009 (watchdog).
- Ícone, logo e traduções das opções.

## 1.0.4

- Libera a sessão de controle presa na central (resposta `f0 f0 01`), causa da recusa
  `0x21` nos comandos depois de uma reconexão.
- Encerra a sessão ao parar o App.

## 1.0.3

- Espera a central confirmar a sessão antes de enviar o comando.
- Log do frame bruto nas recusas.

## 1.0.2

- Detecta queda da conexão com a central (erro ou 60 s sem dados) e deixa as entidades
  indisponíveis.
- Não reenvia comando para um estado em que a central já está.
- Horário em cada linha do log.

## 1.0.1

- Confirmação (`f0 fd 00`) tratada como sucesso; conferência pelo status com reenvio.
- Hora enviada à central no fuso do Home Assistant.

## 1.0.0

- Primeira versão.
