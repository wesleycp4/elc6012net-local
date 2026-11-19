# Instalação

Para ter o controle local são duas etapas:

1. **Fazer a central chegar no relay.** A central abre uma conexão de saída para o
   servidor da nuvem, cujo nome (`amt8000.intelbras.com.br`) é fixo no firmware.
   É preciso desviar essa conexão para o relay — pelo [firmware](#opção-a--firmware-recomendada)
   ou pela [rede](#opção-b--redirecionamento-na-rede).
2. **Rodar o relay**, de preferência como [App do Home Assistant](#app-do-home-assistant)
   ou, fora do HA, como [script Python](#relay-avulso).

> Enquanto a central estiver no relay local, o app e as notificações da Intelbras
> **não funcionam** (a central não fala mais com a nuvem). Para voltar, veja
> [Voltar para a nuvem](#voltar-para-a-nuvem).

---

## Etapa 1 — fazer a central chegar no relay

### Qual opção usar

| Situação | Opção |
|---|---|
| Consegue abrir a central e usar um adaptador USB-serial 3,3 V | **A — firmware** (dispensa qualquer ajuste no roteador) |
| Tem controle do DNS ou do NAT da rede | **B — redirecionamento na rede** |
| Nenhuma das duas | Use a integração via nuvem ([rhacius/ha-elc6012net](https://github.com/rhacius/ha-elc6012net)) |

### Opção A — firmware (recomendada)

Troca-se, na flash do módulo Wi-Fi (ESP8266), o nome do servidor por um nome de
domínio seu, apontado para o IP do relay. A central passa a conectar direto no relay,
sem nenhuma configuração no roteador. Se o IP do relay mudar, basta editar o DNS.

1. Faça o backup da flash e gere a imagem alterada — passo a passo em
   [firmware.md](firmware.md).
2. Crie no seu provedor de DNS um registro **A** para o nome escolhido (ex.:
   `elc.example.com`) apontando para o **IP interno** do relay (ex.: `192.168.1.10`).
   No Cloudflare, deixe o registro como **DNS only** (não proxied).
3. Regrave a flash e religue a central.

O nome resolve para um IP privado: nada fica acessível pela internet. **Não** aponte
para um IP público com redirecionamento de porta — o relay não tem autenticação.

**Internet na reconexão.** Com um domínio público, a central precisa resolver o nome a
cada reconexão. Se a internet cair, a conexão aberta continua, mas uma reconexão nesse
período só acontece quando a internet voltar. Para não depender disso:

- crie também o nome no DNS local do roteador, se ele permitir; ou
- grave o **IP do relay** no lugar do nome (`patch_server.py --novo 192.168.1.10`).
  Dispensa DNS, mas exige IP fixo para o relay e uma nova gravação se ele mudar.
  🟡 Ainda não testado no equipamento: guarde o backup para voltar ao nome.

### Opção B — redirecionamento na rede

O nome `amt8000.intelbras.com.br` precisa resolver para o IP do relay (ou o tráfego
da central precisa ser desviado por NAT). Opções, da mais simples para a mais
trabalhosa:

| Método | Requer | Observação |
|---|---|---|
| Registro DNS local no roteador | roteador com "DNS estático", "host override" ou "DNS records" | só esse nome é afetado |
| AdGuard Home / Pi-hole no HA | roteador que permita trocar o DNS entregue pelo DHCP | toda a rede passa a depender do HA para DNS |
| Rede dedicada para a central | 2º roteador/AP (OpenWrt, Raspberry Pi, PC com [`tools/setup_ap.sh`](../tools/setup_ap.sh)) | não afeta a rede principal |
| DNAT pela origem | roteador com NAT avançado (OpenWrt, MikroTik, pfSense) | não depende de DNS |

**Registro DNS local.** Crie `amt8000.intelbras.com.br → <IP do relay>`. Disponível,
por exemplo, em OpenWrt (`Rede → DHCP e DNS → Hostnames`, ou
`address=/amt8000.intelbras.com.br/<IP>` no dnsmasq), MikroTik (`/ip dns static`),
pfSense/OPNsense (*Host Overrides*) e UniFi (*DNS records*). Roteadores de operadora e
a maioria dos domésticos não oferecem.

**AdGuard Home / Pi-hole.** Crie a reescrita `amt8000.intelbras.com.br → <IP do relay>`
e configure o DHCP do roteador para entregar o IP do HA como **único** servidor DNS —
com um DNS secundário público, a central pode consultá-lo e escapar da reescrita.

**DNAT pela origem.** Desvie todo o TCP da central nas portas 9009 e 8080 para o relay
(a central alterna entre as duas quando a conexão falha). Exige IP fixo para a central
(reserva no DHCP). Exemplo em nftables:

```
nft add rule ip nat prerouting ip saddr <IP da central> tcp dport { 8080, 9009 } \
    ip daddr != <IP do relay> dnat to <IP do relay>:9009
```

O "redirecionamento de porta" comum dos roteadores (internet → LAN) não serve para isso.

**Teste.** De um computador da mesma rede da central:

```bash
nslookup amt8000.intelbras.com.br   # deve responder o IP do relay
```

A central só refaz a consulta ao reconectar: depois de aplicar a regra, desligue e
religue a central.

> Quando a 9009 falha, a central tenta a **8080** do mesmo endereço. Se outro serviço
> escuta na 8080 do host do relay, a central pode ficar presa nele até a próxima
> tentativa na 9009 — prefira deixar essa porta livre (vale também para a opção A).

---

## Etapa 2 — rodar o relay

### App do Home Assistant

Requer Home Assistant OS ou Supervised e o App **Mosquitto broker** com a integração
MQTT.

1. *Configurações → Apps → Loja → ⋮ → Repositórios*: adicione
   `https://github.com/wesleycp4/elc6012net-local`.
2. Instale **ELC 6012 NET Local** e inicie.
3. Na aba *Informações*, confira **Iniciar no boot** ligado (padrão desde a versão
   1.1.0) e ligue o **Watchdog**, que reinicia o App se ele parar — sem o relay, a
   central fica sem servidor.

O App escuta na porta **9009** do host do HA e cria as entidades sozinho via MQTT
Discovery (ver [homeassistant.md](homeassistant.md)). Rode **um** App por vez: o
Local e o Híbrido usam a mesma porta.

### Relay avulso

Em qualquer máquina com Python 3 na rede da central:

```bash
pip install paho-mqtt        # só se for usar --mqtt
python3 relay/elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 \
    --tz America/Sao_Paulo --web 8088 \
    --mqtt <broker>:1883 --mqtt-user <usuário>    # senha em MQTT_PASSWORD
```

Opções e comandos em [relay/README.md](../relay/README.md). Use `--tz` com o seu fuso:
o relay envia a hora para a central, e numa máquina em UTC os eventos sairiam com a
hora errada.

### Verificar

No log do App (ou do relay) deve aparecer, em sequência:

```
== central conectou de ('<IP da central>', ...)
[REGISTRO] central MAC=… modelo=35 -> ack
[TIME] central pediu hora -> enviando
[SESSAO] aberta -> status e comandos liberados
```

---

## Voltar para a nuvem

| Como foi feito | Para reverter |
|---|---|
| Firmware (opção A) | Troque o registro DNS por um **CNAME → `amt8000.intelbras.com.br`** (rápido), ou regrave o backup original da flash (definitivo) |
| Rede (opção B) | Remova a regra de DNS/NAT e religue a central |

---

## Limitações

| Limitação | Impacto |
|---|---|
| Relay é ponto único | Com o relay parado, a central fica sem servidor (sem controle remoto). Controle físico e controle remoto RF continuam funcionando. |
| Sem app Intelbras | No modo local, o app oficial e as notificações da nuvem param. O modo híbrido, que tenta manter os dois, é experimental. |
| Sem autenticação | Porta 9009, painel web e tópicos MQTT não têm senha própria. Mantenha tudo na LAN. |
| Conexão já aberta | Mudanças de DNS/regra só valem na próxima reconexão da central. |
| AdGuard/Pi-hole | Com o HA fora do ar, a rede inteira fica sem DNS. |
| IP da nuvem | DNAT por IP de destino e o `upstream` do modo híbrido quebram se a Intelbras mudar o IP. |
| Atualizações da Intelbras | Uma atualização de firmware pode desfazer o patch (opção A) ou mudar o protocolo. |
