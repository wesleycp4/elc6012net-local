# Redirecionar a central (requisito) e gargalos

**Este é o principal limitador do projeto.** Para qualquer modo local — o relay
puro, o App **Local** ou o App **Híbrido** — a central precisa conectar no seu relay
em vez da nuvem Intelbras. Quem não consegue redirecionar a central não consegue
usar o controle local; nesse caso, a opção é a integração via nuvem (ver
[Sem controle da rede](#sem-controle-da-rede)).

## Por que precisa redirecionar

A central tem o servidor **fixo no firmware**: ela resolve
`amt8000.intelbras.com.br` pelo DNS que recebe do DHCP e conecta na porta **9009**.
Não há onde trocar esse endereço:

- Nas capturas, o nome do servidor aparece **só nas consultas DNS** da central —
  nunca dentro do protocolo 9009 nem nos blocos de configuração.
- O bloco de Wi-Fi (`02 c0`, 96 bytes) tem só **SSID (32 B) + senha (64 B)**, sem
  campos de IP, gateway ou DNS — a central sempre usa DHCP.
- O app Guardian/AMT não tem opção de servidor.

Então o desvio tem que ser feito **na rede**: fazer esse nome (ou o IP da nuvem)
apontar para a máquina do relay.

> **O modo Híbrido também precisa.** Ele muda o que acontece *depois* que a central
> conecta (o relay repassa tudo para a nuvem e injeta comandos locais), mas a
> central só chega no relay se for redirecionada. O ganho do Híbrido é manter o app
> e as notificações da Intelbras, não dispensar o redirecionamento.

## Opções, da mais simples à mais trabalhosa

| # | Opção | Precisa de | Afeta a casa toda? |
|---|---|---|---|
| 1 | Registro de DNS local no roteador | roteador com "DNS estático"/"host override" | não (só esse nome) |
| 2 | AdGuard Home / Pi-hole no HA | roteador que deixa trocar o DNS do DHCP | **sim** (todo o DNS passa pelo HA) |
| 3 | Rede só para a central | um 2º roteador/AP (OpenWrt, Raspberry Pi, PC) | não |
| 4 | DNAT pelo IP da nuvem | roteador com regras de NAT avançadas | não |

### 1. Registro de DNS no roteador (melhor, se existir)

Alguns roteadores permitem criar um nome local. Procure no painel por **DNS
estático**, **DNS local**, **Host override**, **Static DNS**, **hosts** ou
**DNS records**. Crie:

```
amt8000.intelbras.com.br  →  <IP do HA/relay>   (ex.: 192.168.31.10)
```

Costuma existir em: OpenWrt (`Rede → DHCP e DNS → Hostnames`, ou
`address=/amt8000.intelbras.com.br/<IP>` no dnsmasq), MikroTik (`/ip dns static`),
pfSense/OPNsense (*Host Overrides*), UniFi (*DNS records*), ASUS com firmware
Merlin. **Roteadores de operadora e a maioria dos domésticos de fábrica (TP-Link,
Xiaomi, Intelbras…) não têm** — aí vá para a opção 2 ou 3.

### 2. AdGuard Home (ou Pi-hole) no próprio HA

1. Instale o App **AdGuard Home** no HA e, em *Filtros → Reescritas de DNS*, crie
   `amt8000.intelbras.com.br → <IP do HA>`.
2. No roteador, em **LAN/DHCP**, troque o **DNS entregue aos clientes** para o IP do
   HA — **sem DNS secundário público** (8.8.8.8, 1.1.1.1…): se houver um secundário,
   a central pode consultá-lo e escapar da reescrita.
3. Religue a central (ela renova o DHCP e refaz a consulta).

Cuidados:
- **Toda a casa passa a depender do HA para DNS.** Se o HA cair, ninguém navega até
  ele voltar. Deixe o HA estável ou prefira a opção 1/3.
- Se o roteador **não deixa trocar o DNS do DHCP** (comum em roteador de operadora),
  dá para desligar o DHCP do roteador e usar o servidor DHCP do próprio AdGuard —
  mais invasivo, só se souber o que está fazendo.
- Trocar só o DNS *do WAN* do roteador às vezes funciona (o roteador repassa as
  consultas), mas muitos ignoram ou usam cache — teste.

### 3. Rede só para a central (mais isolada)

Um segundo roteador/AP só para a central, com DNS sob seu controle; o WAN dele fica
ligado na sua rede de casa. A central entra no Wi-Fi dele e o DNS dele aponta
`amt8000.intelbras.com.br` para o IP do HA (que ele alcança pela rede de casa).

- Serve: roteador velho com **OpenWrt**, **Raspberry Pi** como AP, ou um Linux/
  notebook com [`tools/setup_ap.sh`](../tools/setup_ap.sh) (foi assim que o projeto
  foi validado).
- Não mexe no DNS da casa. A central troca de rede pelo próprio app Intelbras
  (ou pelo comando de Wi-Fi do [PROTOCOL.md §5](../PROTOCOL.md)).
- Desvantagem: mais um equipamento ligado o tempo todo.

### 4. DNAT pelo IP da nuvem

Em roteadores com NAT avançado (OpenWrt, MikroTik, pfSense), redirecione o tráfego
da central para o IP da nuvem, porta 9009, para o relay:

```
destino 52.67.212.35:9009 (TCP)  →  <IP do HA>:9009
```

Não precisa de DNS, mas é **frágil**: se a Intelbras mudar o IP, para de
funcionar. O "redirecionamento de porta" comum dos roteadores (internet → LAN)
**não serve** para isso. Bom como reforço da opção 1/3.

## Como saber o que o seu roteador permite

1. Abra o painel do roteador (o IP do gateway — ex.: `192.168.31.1` em redes
   `192.168.31.x`, padrão de roteadores Xiaomi).
2. Procure: (a) DNS estático/hosts → opção 1; (b) DNS do servidor DHCP/LAN editável
   → opção 2; (c) nada disso → opção 3, ou trocar por um roteador com OpenWrt.

## Como testar

```bash
# de um PC na mesma rede da central (deve responder o IP do HA, não da Intelbras)
nslookup amt8000.intelbras.com.br
```

Depois **desligue e religue a central** (ela guarda o IP resolvido) e veja no log
do relay/App: `[+] central conectou` e `[SESSAO] aberta`. Para desfazer, remova a
regra e religue a central: ela volta para a nuvem.

## Gargalos e limitações

| Gargalo | Impacto |
|---|---|
| **Redirecionamento obrigatório** | Sem controle de DNS/rede, não há modo local (nem Híbrido). |
| **Relay/HA é ponto único** | HA fora do ar → central sem servidor: sem controle remoto e (no Local) sem nuvem. O controle físico/controle remoto da central continua funcionando. |
| **DNS da casa no HA** (opção 2) | HA fora do ar derruba o DNS de toda a casa. |
| **Cache de DNS da central** | Mudanças só valem após religar a central. |
| **Modo Local sem app Intelbras** | Sem app oficial e sem notificações da nuvem enquanto estiver no relay. |
| **Modo Híbrido não testado** | Pode haver instabilidade na sessão da nuvem; usa o IP fixo `52.67.212.35`. |
| **IP da nuvem pode mudar** | Quebra a opção 4 e o `upstream` do Híbrido (atualizar à mão). |
| **Uma conexão por vez** | Só um relay/App na porta 9009. |
| **Sem autenticação** | A porta 9009, o painel web e os tópicos MQTT não pedem senha além do broker: mantenha tudo **só na LAN**, nunca exponha à internet. |
| **Firmware novo** | Uma atualização da Intelbras pode mudar o servidor, o protocolo ou adicionar TLS e quebrar o modo local. |

## Sem controle da rede

Se não der para redirecionar, use a integração via **nuvem** (o App de nuvem
baseado no projeto do rhacius): funciona no HA sem mexer na rede, mas depende da
internet e da nuvem Intelbras.

| Você tem… | Use |
|---|---|
| Nenhum controle de DNS/rede | App de nuvem (depende da internet) |
| Controle de DNS e não precisa do app Intelbras | **App Local** (validado) |
| Controle de DNS e quer manter app/alertas Intelbras | **App Híbrido** (experimental) |
