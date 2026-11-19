# Status

Estado de cada parte do projeto. Detalhes do protocolo em [PROTOCOL.md](../PROTOCOL.md).

| Símbolo | Significado |
|---|---|
| ✅ | funciona — validado no equipamento |
| 🟡 | mapeado, mas sem validação completa |
| ⬜ | não mapeado |

Testado em: ELC 6012 NET, placa base 1.1.0, módulo Wi-Fi 1.2.11.

## Relay e Home Assistant

| Recurso | Status | Observação |
|---|---|---|
| Registro, hora e manutenção da sessão | ✅ | |
| Liberação de sessão presa (`f0 f0 01`) | ✅ | `f0 f1` + `f0 f0` devolve `00`; feito pelo relay a cada conexão, se preciso |
| Detecção de queda da central | ✅ | erro de conexão ou 60 s sem dados → entidades indisponíveis |
| Leitura de status | ✅ | choque, alarme, zonas, disparo, bypass, relógio, sinal |
| Arme / desarme / choque | ✅ | confirmado pelo status, com reenvio se não mudar |
| Bypass, pânico, PGM | ✅ | pelo console/painel do relay; ainda não expostos no HA |
| Eventos Contact-ID | ✅ | recebidos e confirmados; ainda não expostos no HA |
| Integração MQTT / App Local | ✅ | alarme, choque, disparo, zonas 1–8, sinal Wi-Fi |
| Firmware com endereço próprio (nome) | ✅ | dispensa redirecionamento na rede ([firmware.md](firmware.md)) |
| Firmware com IP no lugar do nome | 🟡 | dispensa DNS e internet; ainda não gravado no equipamento |
| App Híbrido (local + nuvem) | 🟡 | **não validado**: túnel e comandos locais funcionam; o app oficial não reconectou no teste |

## Protocolo

| Item | Status | Observação |
|---|---|---|
| Enquadramento e checksum | ✅ | |
| Sessão de controle `f0 f0` | ✅ | resposta `00` = controle, `01` = só leitura (sessão anterior presa) |
| Status `0b 4a` (164 bytes) | ✅ | campos em PROTOCOL §4.1 |
| Arme/desarme/choque `40 1e` | ✅ | |
| Bypass `40 1f` | ✅ | |
| Pânico `40 1a` | ✅ | silencioso e audível; fogo e médico não existem no ELC |
| PGM `45 af` | ✅ | só com a PGM em modo "acesso via app" |
| Eventos `10 b2` | ✅ | códigos em PROTOCOL §4.7; `412` sem significado conhecido |
| Histórico `39 00` | ✅ | |
| Recusa `f0 fd` | ✅ | `00` = ACK, `21` = sem sessão de controle ou função não permitida |
| Desligar sirene `40 19` | 🟡 | aceito; efeito não observado |
| Leitura de configuração `3f 12` | ✅ | zonas, nome, Wi-Fi, geral, usuários |
| Gravação de configuração `2f 12` | 🟡 | formato visto no tráfego do app; não executado pelo relay |
| PGM temporizada | 🟡 | posição no bloco `03 e0` não confirmada |
| Sinal Wi-Fi (`[163]`) | 🟡 | sem medição independente |
| Pareamento de sensor sem fio | ⬜ | |
| Bateria da central / rede elétrica | ⬜ | eventos existem no firmware; códigos não capturados |

## Limitações conhecidas

- **Zonas com a central desarmada:** a atualização de "zona aberta" é intermitente
  (também no app oficial). Com o alarme armado, a abertura gera disparo imediato.
- **App oficial:** no modo local, o app e as notificações da Intelbras param.
- **Sem autenticação:** o protocolo não autentica o servidor; mantenha o relay só na LAN.

## Pendências

Itens em aberto, por prioridade. Como contribuir: [CONTRIBUTING.md](../CONTRIBUTING.md).

1. **Modo híbrido** — descobrir por que o app oficial não reconecta pelo proxy. Requer
   capturar também o lado da nuvem. Hipótese: sessão presa na central (ver
   [PROTOCOL §3](../PROTOCOL.md), resposta `f0 f0 01`), já que a nuvem recusa login
   com "outra sessão ativa".
2. **Bateria e rede elétrica** — capturar os eventos de falta de energia e bateria
   baixa e expô-los no HA.
3. **Entidades extras no HA** — bypass por zona, último evento, PGM.
4. **Gravação de configuração** — validar `2f 12` com algo reversível (nome de zona)
   antes de blocos sensíveis (Wi-Fi, usuários).
5. **Sirene `40 19`**, **PGM temporizada** e **pareamento de sensor**.
6. **Firmware com IP** — gravar e validar a variante com o IP do relay no lugar do nome.
7. **Serial interna ESP ↔ placa base** — pré-requisito para qualquer firmware próprio.
8. **Integração nativa** — uma integração do Home Assistant (HACS) no lugar do App +
   MQTT funcionaria também em Home Assistant Container/Core.
