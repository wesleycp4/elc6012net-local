# ELC 6012 NET Híbrido (experimental)

> ⚠️ **Experimental.** O túnel com a nuvem e os comandos locais funcionam, mas nos
> testes o app oficial da Intelbras não reconectou através do App. Para uso normal,
> prefira o **ELC 6012 NET Local**.

O App fica entre a central e a nuvem Intelbras:

- repassa o tráfego da central para a nuvem, com o objetivo de manter o app oficial e
  as notificações funcionando;
- publica a central no Home Assistant (mesmas entidades do App Local);
- envia os comandos do Home Assistant numa sessão própria (`inject_session`), separada
  das sessões da nuvem;
- se a internet cair, o controle local continua.

## Antes de iniciar

1. Tenha o **App Mosquitto** rodando.
2. Faça a central conectar no IP deste Home Assistant, porta 9009 (mesmo requisito do
   App Local): https://github.com/wesleycp4/elc6012net-local/blob/main/docs/instalacao.md
3. Não rode junto com o App Local — os dois usam a porta 9009.

## Opções

| Opção | Padrão | Descrição |
|---|---|---|
| `upstream` | `52.67.212.35:9009` | servidor da nuvem Intelbras. Use o IP, não o nome, para não cair no próprio redirecionamento; atualize se a Intelbras mudar o IP |
| `inject_session` | `2` | sessão dos comandos locais. A nuvem atribui uma sessão por cliente conectado (1, 2…); com mais de um cliente, use um número livre (ex.: `5`) |
| `node` | `elc6012_hibrido` | id do dispositivo no MQTT/HA |
| `name` | `ELC 6012 NET (híbrido)` | nome do dispositivo |

## Riscos

- Comportamento da nuvem com um intermediário não está validado; pode haver
  instabilidade na sessão do app oficial.
- Para desfazer: pare o App e desfaça o redirecionamento — a central volta a falar
  direto com a nuvem.
