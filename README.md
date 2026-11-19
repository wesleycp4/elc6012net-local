# elc6012net-local

[![CI](https://github.com/wesleycp4/elc6012net-local/actions/workflows/ci.yaml/badge.svg)](https://github.com/wesleycp4/elc6012net-local/actions/workflows/ci.yaml)
![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)
![Home Assistant App](https://img.shields.io/badge/Home%20Assistant-App-41BDF5.svg)

Controle local, sem nuvem, do eletrificador **Intelbras ELC 6012 NET** — com
integração ao Home Assistant e a documentação do protocolo.

[![Adicionar o repositório ao Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fwesleycp4%2Felc6012net-local)

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
- Zonas 1–8, disparo e sinal Wi-Fi no Home Assistant (descoberta automática via MQTT)
- Bypass, eventos Contact-ID, histórico, pânico e PGM pelo relay (ainda não viram
  entidades)
- Detecta queda da central e libera sozinho a sessão de controle presa
- Sem nuvem; sem internet também, desde que o nome do servidor resolva na rede local
  (ver [limitações](docs/instalacao.md#limitações))

## Apps do Home Assistant

| App | Estado | Para quê |
|---|---|---|
| [**ELC 6012 NET Local**](elc6012net_local) | estável | a central fala só com o Home Assistant |
| [**ELC 6012 NET Híbrido**](elc6012net_hibrido) | ⚠️ não validado | tenta manter a nuvem e o app Intelbras junto com o controle local; nos testes o app oficial não reconectou |

Os dois usam a porta 9009: rode um de cada vez.

Estado detalhado de cada item: [docs/STATUS.md](docs/STATUS.md).

## Instalação

Guia completo em **[docs/instalacao.md](docs/instalacao.md)**. Resumo:

1. Faça a central chegar no relay — pelo [firmware](docs/firmware.md) ou pela
   [rede](docs/instalacao.md#opção-b--redirecionamento-na-rede).
2. No Home Assistant, adicione este repositório (botão acima, ou *Configurações → Apps
   → Loja → ⋮ → Repositórios*) e instale **ELC 6012 NET Local**.
3. As entidades aparecem sozinhas — ver [docs/homeassistant.md](docs/homeassistant.md).

Fora do Home Assistant, o relay roda como script Python: [relay/README.md](relay/README.md).

## Limitações

- Enquanto a central estiver no relay, o **app e as notificações da Intelbras não
  funcionam**. O modo híbrido, que tenta manter os dois, não foi validado.
- Os Apps exigem Home Assistant OS ou Supervised. Em Home Assistant Container/Core,
  rode o relay como script.
- Com a central **desarmada**, a detecção de zona aberta é intermitente (como no app
  oficial).
- O protocolo **não autentica o servidor**. Mantenha o relay acessível só pela LAN.

## Segurança

- Capturas de rede e dumps de flash da central contêm, em texto claro, o SSID e a
  senha do Wi-Fi e o código de acesso. Não publique esses arquivos; o `.gitignore`
  bloqueia `*.pcap` e `*.bin`, e `tools/decode_capture.py` mascara os dados sensíveis.
- Nunca exponha a porta 9009, o painel web do relay ou o broker MQTT à internet.

Política completa e como relatar vulnerabilidades: [SECURITY.md](SECURITY.md).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | especificação do protocolo |
| [`docs/`](docs) | [instalação](docs/instalacao.md), [Home Assistant](docs/homeassistant.md), [firmware](docs/firmware.md), [status](docs/STATUS.md) |
| [`relay/`](relay) | relay local e ponte MQTT (fonte do código) |
| [`elc6012net_local/`](elc6012net_local), [`elc6012net_hibrido/`](elc6012net_hibrido) | Apps do Home Assistant (código copiado de `relay/` por [`scripts/sync_apps.py`](scripts/sync_apps.py)) |
| [`tools/`](tools) | AP para captura, decodificador de capturas, proxy de observação, patch de firmware |
| [`tests/`](tests) | testes do protocolo, da ponte MQTT e do relay contra uma central simulada |

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
