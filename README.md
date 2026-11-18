# elc6012net-local

Controle local, sem nuvem, do eletrificador **Intelbras ELC 6012 NET** — com
integração ao Home Assistant e a documentação do protocolo.

> Projeto independente, sem vínculo com a Intelbras, feito por engenharia reversa do
> próprio equipamento para fins de interoperabilidade. Ele controla uma cerca elétrica
> real: use por sua conta e risco.

## Como funciona

A central mantém uma conexão TCP de saída com o servidor da Intelbras
(`amt8000.intelbras.com.br`, porta 9009), em texto claro. Este projeto fornece um
**relay local** que fala o mesmo protocolo; desviando essa conexão para ele, a central
passa a ser controlada dentro de casa, e o relay a expõe no Home Assistant via MQTT.

```
 ┌──────────┐  firmware ou rede   ┌──────────────┐   MQTT    ┌────────────────┐
 │ Central  │ ──────────────────▶ │ Relay local  │ ────────▶ │ Home Assistant │
 │ ELC 6012 │ ◀── status/comandos │ (App do HA)  │ ◀──────── │                │
 └──────────┘                     └──────────────┘           └────────────────┘
```

O nome do servidor é fixo no firmware da central. Há duas formas de desviar a conexão:

- **Firmware** — gravar no módulo Wi-Fi um nome de domínio seu, apontado para o relay.
  Não exige nada do roteador. ([firmware.md](docs/firmware.md))
- **Rede** — fazer o nome da Intelbras resolver para o relay (DNS local, AdGuard,
  Pi-hole) ou desviar o tráfego por NAT.

## Recursos

- Arme/desarme do alarme e liga/desliga do choque, com confirmação pelo status
- Zonas 1–8, disparo, bypass, sinal Wi-Fi e relógio da central
- Eventos Contact-ID, histórico, pânico e PGM (pelo relay)
- App do Home Assistant com descoberta automática das entidades
- Funciona sem internet

Estado detalhado de cada item: [docs/STATUS.md](docs/STATUS.md).

## Instalação

Guia completo em **[docs/instalacao.md](docs/instalacao.md)**. Resumo:

1. Faça a central chegar no relay — pelo [firmware](docs/firmware.md) ou pela
   [rede](docs/instalacao.md#opção-b--redirecionamento-na-rede).
2. No Home Assistant, adicione este repositório em *Configurações → Apps → Loja →
   Repositórios*, instale **ELC 6012 NET Local** e ative *Iniciar no boot* e *Watchdog*.
3. As entidades aparecem sozinhas — ver [docs/homeassistant.md](docs/homeassistant.md).

Fora do Home Assistant, o relay roda como script Python: [relay/README.md](relay/README.md).

## Limitações

- Enquanto a central estiver no relay, o **app e as notificações da Intelbras não
  funcionam**. O modo híbrido, que tenta manter os dois, é experimental.
- Com a central **desarmada**, a detecção de zona aberta é intermitente (como no app
  oficial).
- O protocolo **não autentica o servidor**. Mantenha o relay acessível só pela LAN.

## Segurança

- Capturas de rede e dumps de flash da central contêm, em texto claro, o SSID e a
  senha do Wi-Fi e o código de acesso. Não publique esses arquivos; o `.gitignore`
  bloqueia `*.pcap` e `*.bin`, e `tools/decode_capture.py` mascara os dados sensíveis.
- Nunca exponha a porta 9009, o painel web do relay ou o broker MQTT à internet.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | especificação do protocolo |
| [`docs/`](docs) | [instalação](docs/instalacao.md), [Home Assistant](docs/homeassistant.md), [firmware](docs/firmware.md), [status](docs/STATUS.md) |
| [`relay/`](relay) | relay local e ponte MQTT |
| [`elc6012net_local/`](elc6012net_local), [`elc6012net_hibrido/`](elc6012net_hibrido) | Apps do Home Assistant |
| [`tools/`](tools) | AP para captura, decodificador de capturas, proxy de observação, patch de firmware |

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md) e as pendências em
[docs/STATUS.md](docs/STATUS.md#pendências). Histórico de mudanças em
[CHANGELOG.md](CHANGELOG.md).

## Créditos

- [rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net) — mapeamento do
  protocolo app ⇄ nuvem e a integração via nuvem que serviu de base.
- [bobaoapae/guardian-api-intelbras](https://github.com/bobaoapae/guardian-api-intelbras)
  — validação cruzada dos opcodes de controle.

## Licença

MIT — ver [LICENSE](LICENSE).
