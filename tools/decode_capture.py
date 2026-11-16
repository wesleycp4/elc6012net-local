#!/usr/bin/env python3
"""
decode_capture.py — decodifica uma captura (.pcap) do protocolo ELC 6012 NET
(central <-> relay/nuvem, TCP 9009). Projeto: elc6012net-local. Stdlib pura.

Mascara automaticamente segredos (Wi-Fi 02c0, usuários/código 0400, e a
abertura de sessão f0f0 que leva o código em claro) para a saída poder ser
compartilhada com segurança. Mesmo assim, NÃO publique .pcap bruto: ele contém
o código e a senha em texto claro. Protocolo: ver ../PROTOCOL.md.

Uso:  python3 decode_capture.py captura.pcap [--port 9009]
"""
import argparse, struct, sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=-3))  # ajuste se precisar

PART = {0x01: "alarme", 0x02: "choque", 0xff: "tudo(255)"}
BLOCKS = {  # addr -> (nome, sensivel?)
    "0000": ("zonas", False), "02b0": ("nome", False),
    "02c0": ("wifi(SSID+senha)", True), "03e0": ("config geral", False),
    "0400": ("usuarios(+codigo)", True),   # tem o código/PINs em claro -> sensível
}

import re
def mask_digits(s):
    """Esconde sequências longas de dígitos (códigos/PINs) de qualquer preview."""
    return re.sub(r"\d{4,}", lambda m: "#" * len(m.group()), s)
# opcodes extras observados (ver PROTOCOL.md §6) — só rotula, não decodifica a fundo
OPCODES = {
    "3faa": "pedir MAC (GET_MAC)", "385b": "consulta 38 5b", "385c": "consulta 38 5c",
    "0b01": "consulta status curta 0b 01", "0060": "consulta 00 60",
    "46a0": "consulta por particao 46 a0", "4610": "consulta/refresh 46 10",
    "4019": "desligar sirene (40 19)", "3900": "historico de eventos (39 00)",
    "3f94": "REGISTRO da central", "f080": "sincronismo de hora",
    # keepalive/ack (f0fe/f0fd/f0f7/f0f1) ficam de fora de propósito: são muito
    # frequentes e floodariam a saída.
}
CID = {"407": "arme/desarme remoto", "409": "arme/desarme controle remoto",
       "130": "disparo de zona", "120": "panico audivel", "122": "panico silencioso",
       "422": "PGM", "306": "programacao alterada", "410": "acesso remoto",
       "412": "download/acesso"}

def contact_id(b: bytes) -> str:
    """Evento 10 b2 (PROTOCOL §4.7): qualificador + código Contact-ID (0 = 0x0a),
    partição, zona/usuário e data/hora do evento."""
    if len(b) < 22:
        return f"ev={b.hex()}"
    q = {1: "E", 3: "R"}.get(b[7], f"?{b[7]:02x}")
    code = "".join(str(0 if x == 0x0a else x) for x in b[8:11])
    part = int.from_bytes(b[11:13], "big"); zu = int.from_bytes(b[13:16], "big")
    t = b[16:22]
    return (f"{q} {code} ({CID.get(code, '?')}) part={part} zona/usuario={zu} "
            f"em {t[0]:02d}/{t[1]:02d}/{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}")

ZONE_ATTR = [(0x01,"habilitada"),(0x02,"inteligente"),(0x04,"temporizada"),
             (0x10,"silenciosa"),(0x20,"parcial"),(0x40,"24h")]

def read_pcap(path):
    data = open(path, "rb").read()
    m = struct.unpack("<I", data[:4])[0]
    endian = "<" if m in (0xa1b2c3d4, 0xa1b23c4d) else ">"
    nano = m in (0xa1b23c4d, 0x4d3cb2a1)
    off = 24
    while off + 16 <= len(data):
        s, fr, cl, ol = struct.unpack(endian + "IIII", data[off:off+16]); off += 16
        yield s + fr/(1e9 if nano else 1e6), data[off:off+cl]; off += cl

def tcp(pkt):
    if len(pkt) < 14 or struct.unpack(">H", pkt[12:14])[0] != 0x0800: return None
    ip = pkt[14:]; ihl = (ip[0] & 0xf) * 4
    if ip[9] != 6: return None
    t = ip[ihl:]; doff = (t[12] >> 4) * 4; iptot = struct.unpack(">H", ip[2:4])[0]
    sp, dp = struct.unpack(">HH", t[0:4])
    return ".".join(map(str, ip[12:16])), sp, ".".join(map(str, ip[16:20])), dp, t[doff:iptot-ihl]

def zone_attrs(v):
    return "+".join(n for b, n in ZONE_ATTR if v & b) or "nenhum"

def decode(path, port):
    # descobre os dois IPs do fluxo 9009
    peers = {}
    pkts = list(read_pcap(path))
    for ts, pkt in pkts:
        r = tcp(pkt)
        if r and (r[1] == port or r[3] == port):
            peers[r[0]] = peers.get(r[0], 0) + 1
    if not peers:
        print("nenhum tráfego na porta", port); return
    # o servidor (relay/nuvem) é quem ESCUTA na porta 9009 (funciona p/ nuvem e local,
    # onde os dois IPs são privados). src na 9009 = servidor; dst na 9009 = servidor.
    relay = None
    for ts, pkt in pkts:
        r = tcp(pkt)
        if not r: continue
        if r[1] == port: relay = r[0]; break
        if r[3] == port: relay = r[2]; break
    print(f"# fluxo porta {port} — relay/nuvem = {relay}\n")
    for ts, pkt in pkts:
        r = tcp(pkt)
        if not r: continue
        src, sp, dst, dp, pl = r
        if (sp != port and dp != port) or not pl: continue
        d = "C->R" if dst == relay else "R->C"
        hh = datetime.fromtimestamp(ts, TZ).strftime("%H:%M:%S")
        cmd = pl[6:8].hex() if len(pl) >= 8 else pl.hex()
        body = pl[8:]
        note = None
        if cmd == "401e" and len(pl) >= 10:
            note = f"COMANDO {PART.get(pl[8],hex(pl[8]))} -> {'LIGA' if pl[9] else 'DESLIGA'}"
        elif cmd == "0b4a" and len(pl) >= 164:
            sig = pl[163]; sig = (256-sig) if sig > 127 else sig
            note = (f"STATUS choque={'on' if pl[30]&1 else 'off'} "
                    f"alarme={'on' if pl[31]&1 else 'off'} zonas={pl[46:48].hex()} "
                    f"disparo={pl[54:56].hex()} bypass={pl[62:64].hex()} sinal=-{sig}dBm")
        elif cmd == "401f":
            note = f"BYPASS (40 1f) dados={body.hex(' ')}"
        elif cmd == "10b2":
            note = f"EVENTO {contact_id(body)}"
        elif cmd == "f0f0" and len(body) >= 1:
            note = "ABERTURA DE SESSAO (f0 f0)  <codigo mascarado>"
        elif cmd == "401a" and len(pl) >= 9:
            PANIC = {0:"silencioso",1:"audivel",2:"fogo",3:"medico"}
            note = f"PANICO (40 1a {pl[8]:02x} = {PANIC.get(pl[8],'tipo?')})"
        elif cmd in OPCODES:
            note = OPCODES[cmd]
            if cmd in ("46a0", "4610") and len(pl) >= 9:
                note += f"  dados={body.hex(' ')}"
        elif cmd in ("3f12", "2f12") and len(body) >= 4:
            addr = body[0:2].hex(); ln = (body[2]<<8)|body[3]; data = body[4:4+ln]
            bname, sens = BLOCKS.get(addr, (f"addr {addr}", False))
            rw = "LER" if cmd == "3f12" else "GRAVAR"
            extra = ""
            if len(data) < ln:
                extra = "  (requisição)"
            elif not sens and data:
                if addr == "0000" and len(data) >= 1:
                    extra = f"  zona1_attr={zone_attrs(data[0])}"
                elif addr == "03e0" and len(data) >= 15:
                    extra = (f"  pulsos={data[3]} pgm1={data[7]} pgm2={data[11]} "
                             f"reportagem={data[14]}")
                else:
                    txt = "".join(chr(c) if 32<=c<127 else "." for c in data[:24])
                    extra = f"  '{mask_digits(txt)}'"
            else:
                extra = "  <dados sensíveis mascarados>"
            note = f"{rw} bloco {bname} (addr {addr}, {ln}B){extra}"
        if note:
            print(f"{hh} {d} {note}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pcap")
    ap.add_argument("--port", type=int, default=9009)
    ns = ap.parse_args()
    decode(ns.pcap, ns.port)
