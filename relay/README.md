# Relay local

`elc_local_relay.py` faz o papel da nuvem Intelbras: a central conecta **nele** e
passa a ser controlada localmente, sem nuvem. **Controle (arme/desarme/choque/tudo)
confirmado ao vivo** (ver [../docs/STATUS.md](../docs/STATUS.md)).

## Como usar
Com a central numa rede onde o seu Linux é o gateway (ver
[../tools/setup_ap.sh](../tools/setup_ap.sh)):

```bash
# 1) sobe o relay com o painel web
python3 elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 --web 8088 --tz America/Sao_Paulo

# 2) redireciona o servidor da nuvem para o relay — por DNS ou DNAT
#    (na rede de casa: ver ../docs/redirecionamento.md):

#  a) DNS (dnsmasq): resolve o host da nuvem para o IP do relay
echo 'address=/amt8000.intelbras.com.br/10.0.0.1' | sudo tee -a /tmp/dnsmasq.conf
sudo pkill dnsmasq; sudo dnsmasq -C /tmp/dnsmasq.conf

#  b) DNAT (nftables) pela ORIGEM: todo TCP 9009/8080 da central vai p/ o relay
#     (não depende de DNS nem do IP da nuvem; a central alterna 9009/8080 na falha)
sudo nft add chain ip nat prerouting '{ type nat hook prerouting priority -100 ; }'
sudo nft add rule ip nat prerouting ip saddr 10.0.0.134 tcp dport '{ 8080, 9009 }' \
    ip daddr != 10.0.0.1 dnat to 10.0.0.1:9009
sudo conntrack -D -s 10.0.0.134   # derruba a conexão atual com a nuvem (ou religue a central)
```

Em segundos a central reconecta no relay (ou desligue/religue a central para
forçar). Quando aparecer `[SESSAO] aberta`, controle de dois jeitos:

- **Painel web** (via principal): `http://127.0.0.1:8088` — botões de choque, arme e
  tudo, com status ao vivo.
- **Terminal (stdin)**:
  `arm | disarm | shockon | shockoff | allon | alloff | status | panic [0-3] |`
  `sirenoff | pgm <1|2> <on|off> | bypass <8 dígitos> | events | raw <hex> | quit`.

O status só é impresso quando muda. Recusas reais da central aparecem como
`[RECUSADO] code 0xNN` (`0x21` = função não suportada/não habilitada, ex.: PGM fora
do modo app) e o relay reabre a sessão e reenvia até 2x; `f0 fd 00` é ACK. Para
arme/desarme/choque o relay ainda confere no status e reenvia se o estado não mudou
(`[OK] … confirmado pelo status`).

**Fuso:** o relay manda a hora para a central. Se a máquina estiver em UTC, use
`--tz America/Sao_Paulo` (senão a central fica 3 h adiantada e os eventos saem com
hora errada).

> ⚠️ O painel aciona uma **cerca elétrica** real e não pede confirmação. Ele faz
> bind só em `127.0.0.1` (local). Enquanto o relay roda, a central **não** fala com
> a Intelbras (sem as notificações pela nuvem deles).

## Modo híbrido / proxy (EXPERIMENTAL, não testado)

Por padrão o relay **substitui** a nuvem: a central fala só com ele, e o app/avisos
da Intelbras param. O modo híbrido (`--upstream`) é diferente: o relay vira um
**túnel** entre a central e a nuvem real — repassa tudo nos dois sentidos (então o
**app oficial e os avisos sonoros continuam funcionando**) e, em paralelo, lê o
status pro HA e **injeta comandos locais**.

```bash
python3 relay/elc_local_relay.py --listen 0.0.0.0:9009 \
    --upstream <IP_DA_NUVEM>:9009 --mqtt SEU_BROKER:1883
```

- A central conecta no relay (via DNS/DNAT), e o relay encaminha pra nuvem real.
- Se a **internet/nuvem cair**, o controle local continua (a conexão central↔relay
  é local); quando volta, o túnel se refaz.
- Os comandos locais são injetados numa **sessão própria (índice 2)** para interferir
  o mínimo possível na sessão que a nuvem usa (índice 1).

> ⚠️ **Experimental e não testado.** Injetar comandos numa sessão que a nuvem também
> usa pode dar conflito ocasional (a nuvem vê respostas de comandos que não mandou).
> Pode funcionar liso ou ser instável — valide com calma. É por isso que este modo
> vive na branch `experimental`, não na `main`.
