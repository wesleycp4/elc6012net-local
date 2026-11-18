# Ferramentas

Utilitários para estudar o protocolo e preparar a central. Use apenas no seu
equipamento e na sua rede.

| Ferramenta | Uso |
|---|---|
| `setup_ap.sh` | transforma um Linux em access point com NAT para a central, para capturar o tráfego: `sudo ./setup_ap.sh <WAN_IF> <AP_IF> <SSID> <SENHA>` |
| `relay_tap.py` | proxy transparente que repassa central ⇄ nuvem e registra os bytes: `python3 relay_tap.py --listen 0.0.0.0:9009 --upstream <IP da nuvem>:9009 --log saida.log` |
| `decode_capture.py` | decodifica um `.pcap` (frames, comandos, eventos Contact-ID), mascarando SSID, senha e código: `python3 decode_capture.py captura.pcap [--port 9009]` |
| `patch_server.py` | troca o servidor da nuvem num dump de flash do módulo Wi-Fi e corrige checksum e SHA256 — ver [firmware.md](../docs/firmware.md) |

Capturas (`*.pcap`) e dumps (`*.bin`) contêm dados sensíveis e são bloqueados pelo
`.gitignore`.
