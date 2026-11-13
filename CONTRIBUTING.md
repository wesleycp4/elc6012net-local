# Como contribuir

Precisa de um ELC 6012 NET e vontade de capturar tráfego. Os **testes abertos**
estão em [docs/STATUS.md](docs/STATUS.md).

## Capturando com segurança
1. Ponha a central numa rede sob seu controle — o jeito mais simples é um Linux
   como gateway/AP: [`tools/setup_ap.sh`](tools/setup_ap.sh).
2. Capture a porta 9009: `sudo tcpdump -i <iface> 'port 9009' -w captura.pcap`.
3. Faça **uma** ação por vez no app, anotando a hora.
4. Decodifique: `python3 tools/decode_capture.py captura.pcap` — ele **mascara**
   SSID/senha automaticamente.

## Enviando
- **Nunca** anexe o `.pcap` cru (contém a senha do seu Wi-Fi e o MAC). Mande a
  **saída decodificada** do `decode_capture.py`, ou um `.pcap` já sanitizado.
- Abra uma issue com: o que fez, a hora de cada ação, e a saída decodificada.

Com isso a gente confirma o item no protocolo e marca ✅ no STATUS.
