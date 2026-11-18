# Contribuindo

Contribuições são bem-vindas — especialmente de quem tem um ELC 6012 NET (ou outra
central da família) para validar os itens pendentes em [docs/STATUS.md](docs/STATUS.md).

## Capturando tráfego

1. Coloque a central numa rede sob seu controle. O mais simples é um Linux como
   access point: [`tools/setup_ap.sh`](tools/setup_ap.sh).
2. Capture: `sudo tcpdump -i <interface> 'port 9009 or port 8080' -w captura.pcap`.
3. Faça **uma ação por vez** no app ou na central e anote o horário de cada uma.
4. Decodifique: `python3 tools/decode_capture.py captura.pcap` (mascara SSID, senha e
   código de acesso).

## Enviando

- **Nunca** publique o `.pcap` ou um dump de flash crus — contêm a senha do Wi-Fi e o
  código de acesso. Envie a saída do `decode_capture.py`.
- Abra uma issue informando: modelo e versões (placa base e módulo, vistos no app), o
  que foi feito, o horário de cada ação e a saída decodificada.

## Código

- Python 3, só biblioteca padrão (exceto `paho-mqtt` na ponte MQTT).
- Mudanças no protocolo devem vir acompanhadas da atualização do
  [PROTOCOL.md](PROTOCOL.md) e do [STATUS](docs/STATUS.md).
- A branch `main` contém só o que foi validado no equipamento; trabalho experimental
  vai para `experimental`.
