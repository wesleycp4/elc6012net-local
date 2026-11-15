# Relay local

`elc_local_relay.py` faz o papel da nuvem Intelbras: a central conecta **nele** e
passa a ser controlada localmente, sem nuvem. **Controle (arme/desarme/choque/tudo)
confirmado ao vivo** (ver [../docs/STATUS.md](../docs/STATUS.md)).

## Como usar
Com a central numa rede onde o seu Linux é o gateway (ver
[../tools/setup_ap.sh](../tools/setup_ap.sh)):

```bash
# 1) sobe o relay com o painel web
python3 elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 --web 8080

# 2) redireciona o servidor da nuvem para o relay — por DNS ou DNAT:

#  a) DNS (dnsmasq): resolve o host da nuvem para o IP do relay
echo 'address=/amt8000.intelbras.com.br/10.0.0.1' | sudo tee -a /tmp/dnsmasq.conf
sudo pkill dnsmasq; sudo dnsmasq -C /tmp/dnsmasq.conf

#  b) DNAT (nftables), como reforço / alternativa:
sudo nft add chain ip nat prerouting '{ type nat hook prerouting priority -100 ; }'
sudo nft add rule ip nat prerouting ip daddr <IP_DA_NUVEM> tcp dport 9009 \
    dnat to 10.0.0.1:9009
```

Em segundos a central reconecta no relay (ou desligue/religue a central para
forçar). Quando aparecer `[SESSAO] aberta`, controle de dois jeitos:

- **Painel web** (via principal): `http://127.0.0.1:8080` — botões de choque, arme e
  tudo, com status ao vivo.
- **Terminal (stdin)**:
  `arm | disarm | shockon | shockoff | allon | alloff | status | panic [0-3] |`
  `sirenoff | pgm <1|2> <on|off> | bypass <8 dígitos> | events | raw <hex> | quit`.

O status só é impresso quando muda, e comandos recusados pela central aparecem como
`[RECUSADO] code 0xNN` (o relay reabre a sessão e reenvia até 2x automaticamente).

> ⚠️ O painel aciona uma **cerca elétrica** real e não pede confirmação. Ele faz
> bind só em `127.0.0.1` (local). Enquanto o relay roda, a central **não** fala com
> a Intelbras (sem as notificações pela nuvem deles).
