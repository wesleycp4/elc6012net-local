#!/usr/bin/env bash
# setup_ap.sh — transforma um Linux (Ubuntu/Debian) em roteador/AP para a
# engenharia reversa do ELC 6012 NET. A central entra no WiFi deste notebook,
# que dá internet via NAT pelo cabo. Todo o tráfego da central passa por aqui.
#
# Uso:  sudo ./setup_ap.sh <WAN_IF> <AP_IF> <SSID> <SENHA_WIFI>
# Ex.:  sudo ./setup_ap.sh eth0 wlan0 elc-lab umaSenhaForte123
#
# Pré-requisito (go/no-go):  iw list | grep -A10 "Supported interface modes"
#   -> precisa listar "* AP" na interface que você vai usar como AP_IF.
#
# Reversível: um reboot desfaz tudo (nada é persistido). Para voltar sem
# reiniciar, pare hostapd/dnsmasq e limpe o nftables (comentários no fim).
set -euo pipefail

WAN_IF="${1:?informe a interface do cabo (WAN), ex.: eth0}"
AP_IF="${2:?informe a interface WiFi do AP, ex.: wlan0}"
SSID="${3:?informe o SSID}"
PASS="${4:?informe a senha do WiFi (>=8 chars)}"
AP_IP="10.0.0.1"
AP_NET="10.0.0.0/24"
DHCP_FROM="10.0.0.50"
DHCP_TO="10.0.0.150"

echo ">> instalando pacotes (precisa de internet pelo cabo)"
apt-get update -qq
apt-get install -y hostapd dnsmasq nftables iw tcpdump >/dev/null

echo ">> liberando $AP_IF do NetworkManager"
nmcli dev set "$AP_IF" managed no 2>/dev/null || true
systemctl stop wpa_supplicant 2>/dev/null || true
rfkill unblock wlan 2>/dev/null || true

echo ">> IP estático em $AP_IF ($AP_IP)"
ip link set "$AP_IF" down
ip addr flush dev "$AP_IF"
ip addr add "$AP_IP/24" dev "$AP_IF"
ip link set "$AP_IF" up

echo ">> hostapd (AP 2.4GHz, canal 6, WPA2)"
cat > /tmp/hostapd.conf <<EOF
interface=$AP_IF
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wmm_enabled=1
auth_algs=1
wpa=2
wpa_passphrase=$PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

echo ">> dnsmasq (DHCP + DNS em $AP_IF)"
pkill dnsmasq 2>/dev/null || true
cat > /tmp/dnsmasq.conf <<EOF
interface=$AP_IF
bind-interfaces
dhcp-range=$DHCP_FROM,$DHCP_TO,12h
dhcp-option=3,$AP_IP
dhcp-option=6,$AP_IP
log-queries
log-dhcp
EOF
dnsmasq -C /tmp/dnsmasq.conf

echo ">> NAT: $AP_NET -> $WAN_IF"
sysctl -w net.ipv4.ip_forward=1 >/dev/null
nft flush ruleset
nft add table ip nat
nft add chain ip nat postrouting '{ type nat hook postrouting priority 100 ; }'
nft add rule ip nat postrouting oifname "$WAN_IF" masquerade
nft add table ip filter
nft add chain ip filter forward '{ type filter hook forward priority 0 ; policy accept ; }'

echo ">> subindo hostapd (deixe este terminal aberto; Ctrl-C para parar o AP)"
echo ">> SSID: $SSID   senha: $PASS   gateway/DNS: $AP_IP"
echo ">> conecte a central neste WiFi e valide no app Guardian."
echo ">> captura (outro terminal):  sudo tcpdump -i $AP_IF 'port 9009' -w captura.pcap"
echo
echo "# para reverter sem reboot:"
echo "#   sudo pkill hostapd dnsmasq ; sudo nft flush ruleset ; sudo nmcli dev set $AP_IF managed yes"
exec hostapd /tmp/hostapd.conf
