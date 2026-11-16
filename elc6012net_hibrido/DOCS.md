# ELC 6012 NET Híbrido (experimental)

> ⚠️ **EXPERIMENTAL — ainda não funciona por completo.** No teste ao vivo de
> 16/11/2026 o túnel com a nuvem e o comando local funcionaram, mas **o app
> oficial da Intelbras não entrou**. A versão atual corrige uma suspeita (respostas
> da sessão local iam para a nuvem), mas falta testar de novo. Use o App
> **ELC 6012 NET Local** para o modo validado.

Neste modo o App fica **no meio** entre a central e a nuvem Intelbras:

- repassa o tráfego da central para a nuvem real → a ideia é **o app oficial e os
  avisos da Intelbras continuarem funcionando** (ainda não confirmado);
- lê o status da central e publica no Home Assistant (mesmas entidades do App
  Local: Cerca, Alarme, Disparo, Zona 1…8);
- **injeta os comandos do HA** direto na central, numa sessão própria (índice 2),
  para interferir o mínimo na sessão que a nuvem usa (índice 1);
- se a internet/nuvem cair, o **controle local continua** (central↔App é local).

## Antes de iniciar

1. **App Mosquitto** rodando.
2. **Redirecione a central para o HA**, igual ao App Local: no DNS da rede,
   `amt8000.intelbras.com.br → IP do HA`; depois religue a central. O Híbrido
   **também exige** esse redirecionamento (ele só mantém a nuvem ligada *depois*
   que a central conecta). Como fazer:
   https://github.com/wesleycp4/elc6012net-local/blob/main/docs/redirecionamento.md
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
