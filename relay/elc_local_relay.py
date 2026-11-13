#!/usr/bin/env python3
"""
elc_local_relay.py — relay LOCAL para o Intelbras ELC 6012 NET.

PROTÓTIPO de bancada. Emula o papel da nuvem Intelbras: a central conecta
AQUI (em vez de amt8000.intelbras.com.br) e passa a ser controlada 100%
localmente, sem nuvem e sem app. Baseado em captura do protocolo real
(central <-> relay, TCP 9009, texto claro, sem autenticação do servidor).

Como pôr a central para conectar aqui (no notebook-gateway da central):
    # redireciona o destino da nuvem para este relay local:
    sudo nft add rule ip nat prerouting iifname "wlp0s20f3" \
        ip daddr 52.67.212.35 tcp dport 9009 dnat to 10.0.0.1:9009
    # (e, se a central também usar o servidor "geral", redirecione o IP dele igual)
    python3 elc_local_relay.py --listen 0.0.0.0:9009

Comandos no terminal (stdin): arm | disarm | shockon | shockoff | allon |
    alloff | status | raw <hex> | quit

NÃO É PRODUÇÃO: enquanto isto roda, a central não fala com a Intelbras
(sem notificações pela nuvem deles). Teste com a cerca ciente disso.
"""
import argparse, json, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

def xck(body: bytes) -> int:
    c = 0
    for b in body: c ^= b
    return c ^ 0xff

def build(session: bytes, payload: bytes) -> bytes:
    body = session + b"\x00" + bytes([len(payload)]) + payload
    return body + bytes([xck(body)])

def bcd(n: int) -> int:
    return ((n // 10) << 4) | (n % 10)

def time_sync_payload() -> bytes:
    n = datetime.now()
    wd = (n.isoweekday() % 7) + 1          # sex -> 6, como na captura
    return bytes([0xf0, 0x80,
                  bcd(n.year % 100), bcd(n.month), bcd(n.day),
                  wd, bcd(n.hour), bcd(n.minute), bcd(n.second)])

def decode_status(p: bytes):
    if len(p) < 164: return f"(status curto: {len(p)}B)"
    choque = "ON" if p[30] & 1 else "off"
    alarme = "ON" if p[31] & 1 else "off"
    zonas  = p[46:48].hex()
    disp   = p[54:56].hex()
    sig    = p[163]; sig = (256 - sig) if sig > 127 else sig
    rel    = f"{p[72]:02d}/{p[73]:02d}/{p[74]:02d} {p[75]:02d}:{p[76]:02d}:{p[77]:02d}"
    return f"choque={choque} alarme={alarme} zonas={zonas} disparo={disp} sinal=-{sig}dBm relogio={rel}"

CMD_MAP = {
    "arm":      bytes.fromhex("401e0101"),   # alarme on  (part 1)
    "disarm":   bytes.fromhex("401e0100"),   # alarme off
    "shockon":  bytes.fromhex("401e0201"),   # choque on  (part 2)
    "shockoff": bytes.fromhex("401e0200"),   # choque off
    "allon":    bytes.fromhex("401eff01"),   # tudo on    (part 255)
    "alloff":   bytes.fromhex("401eff00"),   # tudo off
    "status":   bytes.fromhex("0b4a"),       # pede status
}

class Relay:
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        self.buf = b""
        self.last_status = {}

    def send(self, session: bytes, payload: bytes):
        if not self.sock: 
            print("[!] central não conectada ainda"); return
        frame = build(session, payload)
        with self.lock:
            self.sock.sendall(frame)
        print(f"  -> {frame.hex(' ')}")

    def frames(self):
        """Extrai frames do buffer. 0b4a (status) = len no campo; resto = 7+len."""
        while len(self.buf) >= 8:
            L = self.buf[5]
            cmd = self.buf[6:8]
            if cmd == b"\x0b\x4a" and L == 0xa4:
                total = (self.buf[4] << 8) | self.buf[5]     # 164, status sem checksum
            else:
                total = 7 + L
            if len(self.buf) < total:
                break
            frame, self.buf = self.buf[:total], self.buf[total:]
            yield cmd, frame

    def handle(self, frame: bytes, cmd: bytes):
        c = cmd.hex()
        if c == "0b4a":                      # resposta de status
            print(f"[STATUS] {decode_status(frame)}")
            if len(frame) >= 164:
                self.last_status = {
                    "choque": bool(frame[30] & 1), "alarme": bool(frame[31] & 1),
                    "zonas": frame[46:48].hex(), "disparo": frame[54:56].hex(),
                    "bypass": frame[62:64].hex(),
                    "ts": datetime.now().strftime("%H:%M:%S")}
        elif c == "10b2":                    # central reportando evento
            print(f"[EVENTO] {frame[8:].hex(' ')}")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c[:2] == "3f" or len(frame) > 50:   # registro (MAC+modelo)
            mac = frame[11:17].hex(":")
            print(f"[REGISTRO] central MAC={mac} modelo={frame[17]:02x} -> ack")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c == "f0f7":
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c == "f080":
            print("[TIME] central pediu hora -> enviando")
            self.send(b"\x00\x00\x00\x00", time_sync_payload())
        elif c == "f0f0":                    # confirmação de sessão (resposta da central)
            print(f"[SESSAO] central confirmou: {frame[8:-1].hex()}")
        else:
            print(f"[??] {frame.hex(' ')} -> ack")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))

    def reader(self):
        while True:
            data = self.sock.recv(4096)
            if not data:
                print("[!] central desconectou"); return
            self.buf += data
            for cmd, frame in self.frames():
                self.handle(frame, cmd)

    def poller(self, interval):
        while True:
            time.sleep(interval)
            if self.sock:
                try: self.send(b"\x00\x00\x00\x01", CMD_MAP["status"])
                except OSError: return


PANEL_HTML = """<!doctype html><html lang=pt-br><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>ELC 6012 NET — relay local</title><style>
:root{--bg:#0f1115;--fg:#e8eaed;--card:#1a1d24;--line:#2a2f3a;--on:#2e7d32;--off:#555;--red:#c62828}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.5 system-ui,sans-serif;padding:16px;max-width:560px;margin:auto}
h1{font-size:20px}.row{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
button{flex:1;min-width:120px;padding:14px;border:1px solid var(--line);border-radius:12px;
background:var(--card);color:var(--fg);font-size:15px;cursor:pointer}button:active{opacity:.6}
.st{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.st div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.b{font-weight:600}.on{color:#66bb6a}.off{color:#9aa0a8}small{color:#9aa0a8}
</style></head><body><h1>Cerca elétrica — relay local</h1>
<small id=ts>aguardando status…</small>
<div class=row><button onclick=cmd('shockon')>⚡ Choque ON</button>
<button onclick=cmd('shockoff')>Choque OFF</button></div>
<div class=row><button onclick=cmd('arm')>🛡 Armar</button>
<button onclick=cmd('disarm')>Desarmar</button></div>
<div class=row><button onclick=cmd('allon')>Tudo ON</button>
<button onclick=cmd('alloff')>Tudo OFF</button></div>
<div class=st>
<div>Choque <span class=b id=choque>—</span></div>
<div>Alarme <span class=b id=alarme>—</span></div>
<div>Zonas abertas <span class=b id=zonas>—</span></div>
<div>Disparo <span class=b id=disparo>—</span></div></div>
<script>
async function cmd(c){await fetch('/cmd/'+c,{method:'POST'});setTimeout(upd,500)}
async function upd(){try{let s=await(await fetch('/status')).json();
document.getElementById('ts').textContent='último status '+(s.ts||'—');
set('choque',s.choque);set('alarme',s.alarme);
document.getElementById('zonas').textContent=s.zonas||'—';
document.getElementById('disparo').textContent=s.disparo||'—';}catch(e){}}
function set(id,v){let e=document.getElementById(id);e.textContent=v?'ON':'off';
e.className='b '+(v?'on':'off')}
upd();setInterval(upd,3000)
</script></body></html>"""

def start_web(relay, port):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="text/html"):
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.end_headers(); self.wfile.write(body.encode())
        def do_GET(self):
            if self.path == "/status":
                self._send(200, json.dumps(relay.last_status), "application/json")
            else:
                self._send(200, PANEL_HTML)
        def do_POST(self):
            name = self.path.rsplit("/", 1)[-1]
            if name in CMD_MAP:
                relay.send(b"\x00\x00\x00\x01", CMD_MAP[name]); self._send(200, "ok", "text/plain")
            else:
                self._send(404, "comando desconhecido", "text/plain")
    httpd = HTTPServer(("0.0.0.0", port), H)
    print(f"[web] painel em http://0.0.0.0:{port}")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="0.0.0.0:9009")
    ap.add_argument("--poll", type=int, default=15)
    ap.add_argument("--web", type=int, default=0, help="porta do painel web (0 = desligado)")
    ns = ap.parse_args()
    host, port = ns.listen.rsplit(":", 1)
    r = Relay()
    if ns.web:
        start_web(r, ns.web)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, int(port))); srv.listen(1)
    print(f"relay local escutando em {host}:{port}. Aguardando a central...")
    print("comandos: arm disarm shockon shockoff allon alloff status raw <hex> quit")

    def accept_loop():
        while True:
            conn, addr = srv.accept()
            print(f"== central conectou de {addr}")
            r.sock = conn
            threading.Thread(target=r.reader, daemon=True).start()
            threading.Thread(target=r.poller, args=(ns.poll,), daemon=True).start()
    threading.Thread(target=accept_loop, daemon=True).start()

    for line in sys.stdin:
        cmd = line.strip().lower()
        if cmd == "quit": break
        elif cmd in CMD_MAP:
            r.send(b"\x00\x00\x00\x01", CMD_MAP[cmd])
        elif cmd.startswith("raw "):
            r.send(b"\x00\x00\x00\x01", bytes.fromhex(cmd[4:].replace(" ", "")))
        elif cmd:
            print("comando desconhecido")

if __name__ == "__main__":
    main()
