# ELC 6012 NET Híbrido (experimental)

> ⚠️ **EXPERIMENTAL — não testado ao vivo.** Use o App **ELC 6012 NET Local** para
> o modo validado. Este App existe para testar o "melhor dos dois mundos".

Neste modo o App fica **no meio** entre a central e a nuvem Intelbras:

- repassa todo o tráfego para a nuvem real → **o app oficial e os avisos sonoros
  da Intelbras continuam funcionando**;
- lê o status da central e publica no Home Assistant (mesmas entidades do App
  Local: Cerca, Alarme, Disparo, Zona 1…8);
- **injeta os comandos do HA** direto na central, numa sessão própria (índice 2),
  para interferir o mínimo na sessão que a nuvem usa (índice 1);
- se a internet/nuvem cair, o **controle local continua** (central↔App é local).

## Antes de iniciar

1. **App Mosquitto** rodando.
2. **Redirecione a central para o HA**, igual ao App Local: no DNS da rede,
   `amt8000.intelbras.com.br → IP do HA`; depois religue a central.
3. A opção `upstream` usa o **IP** da nuvem (padrão `52.67.212.35:9009`), para não
   cair no próprio redirecionamento de DNS. Se a Intelbras mudar o IP, atualize.
4. **Só um App por vez** na porta 9009 — pare o App Local antes.

## Riscos conhecidos

- A nuvem pode receber respostas de comandos que ela não enviou (os nossos). O
  protocolo parece tolerar, mas pode haver instabilidade ou a sessão da nuvem
  re-sincronizar. Teste com calma, perto da central.
- Se algo ficar estranho, pare este App e desfaça o redirecionamento de DNS: a
  central volta a falar direto com a nuvem.

## Opções

| Opção | Padrão | Para quê |
|---|---|---|
| `upstream` | `52.67.212.35:9009` | Endereço da nuvem Intelbras real |
| `node` | `elc6012_hibrido` | ID do dispositivo no MQTT/HA |
| `name` | `ELC 6012 NET (híbrido)` | Nome do dispositivo no HA |
