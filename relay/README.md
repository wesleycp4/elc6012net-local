# Relay local

`elc_local_relay.py` faz o papel da nuvem Intelbras: a central conecta **nele** e
passa a ser controlada localmente, sem nuvem. Protótipo — enquadramento validado
contra frames reais, **validação ao vivo na central é um teste aberto**
(ver [../docs/STATUS.md](../docs/STATUS.md)).

## Como testar (bancada)
Com a central numa rede onde o seu Linux é o gateway (ver
[../tools/setup_ap.sh](../tools/setup_ap.sh)):

```bash
# 1) sobe o relay
python3 elc_local_relay.py --listen 0.0.0.0:9009

# 2) redireciona o destino da nuvem para o relay (ajuste a interface/IP):
sudo nft add rule ip nat prerouting iifname "wlp0s20f3" \
    ip daddr <IP_DA_NUVEM> tcp dport 9009 dnat to <IP_DO_RELAY>:9009
```

Em segundos a central reconecta no relay. Comandos no terminal:
`arm | disarm | shockon | shockoff | allon | alloff | status | raw <hex> | quit`.

## Painel web (experimental)
Adicione `--web 8080` para um painel local (botões + status) em `http://<ip>:8080`,
útil inclusive para o teste de bancada:
```bash
python3 elc_local_relay.py --listen 0.0.0.0:9009 --web 8080
```

> Enquanto o relay roda, a central **não** fala com a Intelbras (sem notificações
> pela nuvem deles). Teste com a cerca ciente disso.
