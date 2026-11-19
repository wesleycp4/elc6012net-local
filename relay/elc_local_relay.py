#!/usr/bin/env python3
"""
elc_local_relay.py — relay local para o Intelbras ELC 6012 NET.

Faz o papel do servidor da nuvem Intelbras: a central conecta aqui e passa a ser
controlada localmente. Protocolo em PROTOCOL.md; instalação (inclusive como fazer a
central chegar até aqui) em docs/instalacao.md.

    python3 elc_local_relay.py --listen 0.0.0.0:9009 --poll 5 --tz America/Sao_Paulo \
        [--web 8088] [--mqtt broker:1883 --mqtt-user usuario]

Controle: Home Assistant via MQTT (--mqtt), painel web local (--web) ou stdin:
    arm | disarm | shockon | shockoff | allon | alloff | status |
    panic [0|1] | sirenoff | pgm <1|2> <on|off> | bypass <8 dígitos> |
    events | raw <hex> | quit

Aciona uma cerca elétrica real. Enquanto a central estiver aqui, ela não fala com a
nuvem Intelbras.
"""
import argparse, builtins, json, os, signal, socket, struct, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

_print = builtins.print


def _ts_print(*a, **k):
    """print com horário (HH:MM:SS) no início de cada linha do log."""
    _print(datetime.now().strftime("%H:%M:%S"), *a, **k)


SESSION_ACK_TIMEOUT = 3.0   # s esperando a central confirmar a reabertura de sessão
IDLE_TIMEOUT_MIN = 60   # s sem receber nada da central => conexão considerada morta


def xck(body: bytes) -> int:
    c = 0
    for b in body: c ^= b
    return c ^ 0xff

def build(session: bytes, payload: bytes) -> bytes:
    # campo de tamanho = 2 bytes big-endian (len do payload). Para payloads <=255
    # dá o mesmo byte-a-byte da captura; para blocos de config (>255B) fica correto.
    body = session + struct.pack(">H", len(payload)) + payload
    return body + bytes([xck(body)])

def bcd(n: int) -> int:
    return ((n // 10) << 4) | (n % 10)

# Fuso da hora enviada à central (f0 80). A nuvem manda a hora LOCAL (ex.: Brasília);
# se a máquina do relay estiver em UTC, a central fica 3h adiantada e os eventos/
# histórico saem com hora errada. Use --tz America/Sao_Paulo (ou a env TZ).
TZ = None

def set_tz(name: str):
    global TZ
    if not name:
        return
    try:
        from zoneinfo import ZoneInfo
        TZ = ZoneInfo(name)
    except Exception as e:           # sem tzdata no sistema: segue na hora local da máquina
        print(f"[!] fuso '{name}' indisponível ({e}); usando a hora local da máquina")

def time_sync_payload() -> bytes:
    n = datetime.now(TZ)
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

# Abertura da sessão de controle (PROTOCOL §3). Payload fixo, igual ao usado pela
# nuvem; libera status e comandos. A variante `f0 f0 01 <código> 10 00` abre uma
# sessão só de leitura (comandos recebem recusa).
SESSION_OPEN_HEX = "f0f0030306050900000001"

# comandos que a CENTRAL envia para o relay (usados para re-sincronizar frames)
RX_CMDS = {b"\x0b\x4a", b"\xf0\xfd", b"\xf0\xfe", b"\xf0\xf0", b"\xf0\xf7",
           b"\xf0\xf1", b"\xf0\x80", b"\x3f\x94", b"\x39\x00", b"\x10\xb2",
           b"\x40\x1e", b"\x40\x1f", b"\x40\x1a", b"\x45\xaf",
           b"\x2f\x12", b"\x3f\x12"}

def valid_header(b: bytes) -> bool:
    """Cabeçalho plausível: sessão `00 0N 00 00` + comando conhecido."""
    return (len(b) >= 8 and b[0] == 0 and b[2] == 0 and b[3] == 0
            and b[1] <= 0x0f and b[6:8] in RX_CMDS)

def split_frames(buf: bytes):
    """Separa os frames completos de `buf` (framing da central), re-sincronizando
    pelo cabeçalho. Retorna (lista de (cmd, frame), resto). Usado pelo reader
    (modo substituir) e pelo tap (modo proxy)."""
    out = []
    while len(buf) >= 8:
        if not valid_header(buf):
            buf = buf[1:]; continue                # ressync: pula byte de lixo
        L = (buf[4] << 8) | buf[5]
        cmd = buf[6:8]
        total = L if (cmd == b"\x0b\x4a" and L == 0xa4) else 7 + L
        if len(buf) < total:
            break
        out.append((cmd, buf[:total])); buf = buf[total:]
    return out, buf

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
        self._last_status_key = None
        self.code = b""          # (não usado para a sessão de controle; ver open_session)
        self.session_open = bytes.fromhex(SESSION_OPEN_HEX)
        self.session_opened = False
        self._sess_ack = threading.Event()   # setado quando a central confirma o f0f0
        self._sess_code = None          # último código da resposta f0 f0 (0 = controle liberado)
        self._sess_reset_done = False   # já tentou f0f1+f0f0 nesta conexão
        self.SID = b"\x00\x00\x00\x01"  # índice de sessão deste relay
        self._pending_cmd = None        # (opcode, ts, retry) do comando, p/ detectar NACK
        self._last_control = None       # último payload de controle, p/ reenviar numa recusa
        self._ctrl_lock = threading.Lock()   # serializa control() (stdin/web/MQTT/retry)
        self._ctrl_seq = 0              # muda a cada envio; invalida verificações antigas
        self.mqtt = None                # ponte MQTT→Home Assistant (opcional, --mqtt)
        # modo PROXY/híbrido (experimental, --upstream): repassa p/ a nuvem real e
        # injeta comandos numa sessão própria (índice 2) p/ não brigar com a sessão
        # da nuvem (índice 1).
        self.proxy = False
        self.upstream = None            # (host, porta) da nuvem real
        self.up = None                  # socket upstream (p/ a nuvem)
        self.inject_sid = b"\x00\x00\x00\x02"
        self.tap_buf = b""
        self.fwd_buf = b""             # central->nuvem pendente (filtro da sessão injetada)

    def send(self, session: bytes, payload: bytes, quiet: bool = False) -> bool:
        """Envia um frame. Devolve False se a central não está conectada ou se o
        envio falhou (nesse caso a conexão é encerrada e o HA marca indisponível)."""
        conn = self.sock
        if not conn:
            print("[!] central não conectada"); return False
        frame = build(session, payload)
        try:
            with self.lock:
                conn.sendall(frame)
        except OSError as e:
            self.drop(conn, f"falha ao enviar: {e.__class__.__name__}")
            return False
        if not quiet:                      # poll/keepalive passam quiet=True (não poluem o terminal)
            print(f"  -> {frame.hex(' ')}")
        return True

    def drop(self, conn, reason: str):
        """Encerra a conexão `conn`. Se for a conexão atual, limpa o estado e marca
        o dispositivo como indisponível; a central reconecta sozinha."""
        with self.lock:
            current = self.sock is conn
            up = getattr(self, "up", None) if current else None
            if current:
                self.sock = None
                if up is not None:
                    self.up = None
                self.session_opened = False
                self._pending_cmd = None
        for s in (conn, up):
            if s is None:
                continue
            try:
                s.close()
            except OSError:
                pass
        if current:
            print(f"[!] central desconectou ({reason}) — aguardando reconexão")
            if self.mqtt:
                self.mqtt.set_available(False)

    def frames(self):
        """Extrai frames do buffer, re-sincronizando pelo cabeçalho.

        Por que não usar só 7+len nem o checksum:
        - A central às vezes manda f0fd/f0fe com um byte 00 extra, mas o campo de
          tamanho continua `00 02` — então 7+len consome 1 byte a menos e sobra
          lixo.
        - O checksum recebido NÃO é o nosso xck (ex.: f0fe vem com f1, xck daria
          f2) e o status 164B nem tem checksum — não serve de âncora.
        Então, a cada frame, exigimos um cabeçalho plausível (`00 0N 00 00` +
        comando conhecido). Se o próximo byte não for um cabeçalho válido (o byte
        extra), descartamos 1 byte e realinhamos no próximo frame. Isso se
        autocorrige: um f0fd/f0fe fica no máx. 1 byte torto (é só ack, não
        importa) e status/eventos/comandos voltam a cair certo."""
        out, self.buf = split_frames(self.buf)
        for cmd, frame in out:
            yield cmd, frame

    def _update_status(self, frame: bytes):
        """Atualiza/estado + imprime na mudança + publica no MQTT. Sem envios."""
        key = frame[30:32] + frame[46:48] + frame[54:56] + frame[62:64] if len(frame) >= 164 else frame
        if key != self._last_status_key:
            print(f"[STATUS] {decode_status(frame)}")
            self._last_status_key = key
        if len(frame) >= 164:
            self.last_status = {
                "choque": bool(frame[30] & 1), "alarme": bool(frame[31] & 1),
                "zonas": frame[46:48].hex(), "disparo": frame[54:56].hex(),
                "bypass": frame[62:64].hex(),
                "ts": datetime.now().strftime("%H:%M:%S")}
            if self.mqtt:
                self.mqtt.publish_state(self.last_status)

    def tap(self, frame: bytes, cmd: bytes):
        """Modo PROXY: só OBSERVA os frames (não envia nada — quem fala o protocolo
        com a central é a nuvem). Atualiza status/HA, loga eventos, detecta NACK dos
        NOSSOS comandos injetados."""
        c = cmd.hex()
        if c == "0b4a":
            self._update_status(frame)
        elif c == "10b2":
            print(f"[EVENTO] {frame[8:].hex(' ')}")
        elif c == "f0fd":
            self._on_f0fd(frame)
        elif c == "f0f0" and frame[1] == self.inject_sid[3]:
            self._sess_ack.set()            # confirmação da NOSSA sessão injetada

    def handle(self, frame: bytes, cmd: bytes):
        c = cmd.hex()
        if c == "0b4a":                      # resposta de status
            self._update_status(frame)
        elif c == "10b2":                    # central reportando evento
            print(f"[EVENTO] {frame[8:].hex(' ')}")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c == "3f94":                    # registro (MAC + modelo)
            mac = frame[11:17].hex(":")
            print(f"[REGISTRO] central MAC={mac} modelo={frame[17]:02x} -> ack")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c in ("f0fd", "f0fe"):          # f0fe=ACK; f0fd=resposta (ACK/recusa) ou keepalive
            if c == "f0fd":
                self._on_f0fd(frame)
        elif c == "3900":                    # resposta de histórico de eventos
            self._hist(frame[8:])
        elif c == "f0f7":
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))
        elif c == "f080":
            print("[TIME] central pediu hora -> enviando")
            self.send(b"\x00\x00\x00\x00", time_sync_payload())
            self.open_session()
        elif c == "f0f0":                    # confirmação de sessão (resposta da central)
            code = frame[8] if len(frame) >= 9 else 0
            self._sess_code = code
            self._sess_ack.set()
            if code != 0x00:
                # Visto: 0x01 depois de uma reconexão sem a central reiniciar — a sessão
                # da conexão anterior continua presa na central e a nova só lê status
                # (comandos voltam 0x21). Encerra (f0 f1) e reabre, uma vez por conexão.
                print(f"[SESSAO] central respondeu código 0x{code:02x} (sem controle): {frame.hex(' ')}")
                if not self._sess_reset_done:
                    self._sess_reset_done = True
                    threading.Thread(target=self.reset_session, args=(self.sock,), daemon=True).start()
                elif not self.session_opened:
                    print("[SESSAO] continua sem controle após reiniciar a sessão: status funciona, "
                          "comandos serão recusados. Religar a central libera.")
            elif self._sess_reset_done and not getattr(self, "_reset_ok_logged", False):
                self._reset_ok_logged = True
                print("[SESSAO] reaberta com controle liberado (código 0x00)")
            if not self.session_opened:      # só avisa na 1ª abertura (reaberturas por comando ficam quietas)
                print("[SESSAO] aberta -> status e comandos liberados" if code == 0
                      else "[SESSAO] aberta só para leitura")
            self.session_opened = True
        else:
            print(f"[??] {frame.hex(' ')} -> ack")
            self.send(b"\x00\x00\x00\x00", bytes.fromhex("f0fe"))

    def _on_f0fd(self, frame: bytes):
        """Resposta da central logo após um comando nosso: `f0 fd <código>`.
        - 0x00 = ACK genérico ("ok, sem dados") — NÃO é recusa (bypass,
          choque e consultas respondem f0fd 00 e o efeito acontece).
        - 0x21 = recusa: função não suportada/não habilitada (PGM fora do modo app,
          pânico fogo/médico no ELC) ou sessão de controle caída.
        - num keepalive o byte é o checksum (xck) — ignorado.
        Reenvia (até 2x, reabrindo a sessão) só numa recusa real."""
        if not (self._pending_cmd and time.time() - self._pending_cmd[1] < 1.5):
            return
        code = frame[8] if len(frame) >= 9 else None
        op, _ts, retry = self._pending_cmd
        if code is None or code == xck(frame[:8]):
            return                          # keepalive, não é resposta ao comando
        self._pending_cmd = None
        if code == 0x00:
            return                          # ACK
        if op == "401e":                    # arme/desarme/choque: _verify confere pelo status
            print(f"[RECUSADO] {op} code 0x{code:02x} ({frame.hex(' ')}) — conferindo pelo status")
            return
        if retry < 2 and self._last_control is not None:
            print(f"[RECUSADO] {op} code 0x{code:02x} — reabrindo e reenviando ({retry+1}/2)...")
            pl = self._last_control
            threading.Thread(target=lambda: self.control(pl, retry + 1), daemon=True).start()
        else:
            print(f"[RECUSADO] {op} code 0x{code:02x} — desisti. 0x21 = função não suportada "
                  f"ou não habilitada para controle remoto (ex.: PGM fora do modo app).")

    def _verify(self, payload: bytes, retry: int, seq: int):
        """Para arme/desarme/choque (40 1e): confere no status se o estado mudou e
        reenvia (até 2x) se não mudou. Cobre o caso de a central ignorar o comando
        sem mandar recusa."""
        part, want = payload[2], bool(payload[3])
        keys = {0x01: ("alarme",), 0x02: ("choque",), 0xff: ("alarme", "choque")}.get(part)
        if not keys:
            return
        conn = self.sock
        time.sleep(2.5)
        if self.sock is not conn or seq != self._ctrl_seq:
            return
        if not self.send(self.my_sid, CMD_MAP["status"], quiet=True):
            return
        time.sleep(1.5)
        if self.sock is not conn or seq != self._ctrl_seq or not self.last_status:
            return
        if all(self.last_status.get(k) == want for k in keys):
            print(f"[OK] {payload.hex()} confirmado pelo status")
        elif retry < 2:
            print(f"[!] {payload.hex()} não refletiu no status — reenviando ({retry+1}/2)...")
            self.control(payload, retry + 1)
        else:
            print(f"[!] {payload.hex()} não refletiu no status após retentativas "
                  f"(zona aberta impede armar? central ocupada?)")

    def reader(self, conn):
        # Atado à conexão: sai se outra conexão assumir (a central reconecta no churn de WiFi).
        reason = "conexão fechada pela central"
        while self.sock is conn:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                reason = f"sem dados há {conn.gettimeout():.0f}s"
                break
            except OSError as e:
                reason = f"erro de conexão: {e.__class__.__name__}"
                break
            if not data:
                break
            if self.sock is not conn:
                return
            self.buf += data
            for cmd, frame in self.frames():
                self.handle(frame, cmd)
        self.drop(conn, reason)

    def _hist(self, body):
        """Decodifica uma página de histórico (39 00 <pág> <eventos de 15B>)."""
        recs = body[2:]
        for i in range(0, len(recs) - 14, 15):
            r = recs[i:i+15]
            ts = f"{r[9]:02d}/{r[10]:02d}/{r[11]:02d} {r[12]:02d}:{r[13]:02d}:{r[14]:02d}"
            print(f"[HIST] {ts}  codigo={r[0:9].hex()}")

    def reset_session(self, conn):
        """Encerra a sessão de controle presa (f0 f1) e abre de novo (f0 f0)."""
        print("[SESSAO] encerrando a sessão anterior (f0 f1) e reabrindo...")
        with self._ctrl_lock:
            if self.sock is not conn or not self.send(self.my_sid, bytes.fromhex("f0f1")):
                return
            time.sleep(3.0)                 # a central fecha a sessão ~2 s após o f0 f1
            if self.sock is not conn:
                return
            self._sess_ack.clear()
            self.send(self.my_sid, self.session_open, quiet=True)
            self._sess_ack.wait(SESSION_ACK_TIMEOUT)

    def open_session(self):
        """Abre a sessão de CONTROLE (f0 f0 03 03 06 05 09 00 00 00 01, fixa).
        Autoriza status E comandos. Não leva o código: a central não autentica
        o servidor (o código não aparece no tráfego)."""
        print("[SESSAO] abrindo sessão de controle...")
        self.send(self.SID, self.session_open)

    def poller(self, conn, interval):
        while self.sock is conn:
            time.sleep(interval)
            if self.sock is conn and self.session_opened:
                if not self.send(self.SID, CMD_MAP["status"], quiet=True):
                    return

    def _already(self, payload) -> bool:
        """Arme/desarme/choque já no estado pedido: não envia (a central recusaria
        com 0x21) e republica o estado para o HA corrigir a interface."""
        if payload[:2] != b"\x40\x1e" or len(payload) < 4 or not self.last_status:
            return False
        keys = {0x01: ("alarme",), 0x02: ("choque",), 0xff: ("alarme", "choque")}.get(payload[2])
        want = bool(payload[3])
        if not keys or not all(self.last_status.get(k) == want for k in keys):
            return False
        print(f"[=] {payload.hex()}: já está nesse estado — nada a enviar")
        if self.mqtt:
            self.mqtt.publish_state(self.last_status)
        return True

    def control(self, payload, _retry=0):
        """Envia um comando de controle. Reabre a sessão (f0f0, quiet) e, após uma
        pequena folga p/ a central processar, manda o comando — como o app. NUNCA
        manda f0f1 (=DISCONNECT, derruba a sessão -> NACK 0x21). Numa recusa, o
        handle() chama isto de novo (até 2x) reabrindo e reenviando."""
        if not self.sock:
            print("[!] central não conectada — comando descartado"); return
        if _retry == 0 and self._already(payload):
            return
        with self._ctrl_lock:                                 # serializa a sequência inteira
            if _retry == 0:
                self._last_control = payload
            self._ctrl_seq += 1
            seq = self._ctrl_seq
            # No modo proxy os comandos vão numa sessão própria (inject_session) p/ não
            # brigar com a sessão da nuvem; no modo substituir usamos a nossa (1).
            sid = self.my_sid
            self._sess_ack.clear()
            if not self.send(sid, self.session_open, quiet=True):        # reabre a sessão de controle
                print("[!] comando não enviado: central desconectada"); return
            # espera a central confirmar a reabertura (f0 f0) antes do comando: com sinal
            # Wi-Fi fraco a confirmação pode passar de 150 ms e o comando cai em 0x21.
            t0 = time.time()
            acked = self._sess_ack.wait(SESSION_ACK_TIMEOUT)
            if acked and self._sess_code not in (None, 0):
                print(f"[!] sessão sem controle (código 0x{self._sess_code:02x}): o comando deve ser recusado")
            if acked:
                if time.time() - t0 > 0.5:
                    print(f"[SESSAO] reabertura confirmada em {time.time() - t0:.1f}s")
                time.sleep(0.05)
            else:
                print(f"[SESSAO] sem confirmação da reabertura em {SESSION_ACK_TIMEOUT:.0f}s — enviando mesmo assim")
            self._pending_cmd = (payload[:2].hex(), time.time(), _retry)
            if not self.send(sid, payload):                       # manda o comando
                print("[!] comando não enviado: central desconectada"); return
        if payload[:2] == b"\x40\x1e" and len(payload) >= 4:
            threading.Thread(target=self._verify, args=(payload, _retry, seq), daemon=True).start()

    @property
    def my_sid(self) -> bytes:
        """Sessão usada pelos NOSSOS envios: a injetada no modo proxy, a 1 no local."""
        return self.inject_sid if self.proxy else self.SID

    # ----- modo PROXY/híbrido (experimental) -----
    def _c2u_filter(self, data: bytes) -> bytes:
        """central -> nuvem: devolve o que deve seguir p/ a nuvem, SEM os frames da
        nossa sessão injetada (respostas de status/comando na sessão 2). Repassar
        esses frames poluía a sessão da nuvem — suspeita no teste em que o app
        oficial não entrou. Bytes que não formam um frame nosso seguem crus."""
        n = self.inject_sid[3]
        b = self.fwd_buf + data
        out = bytearray(); i = 0
        while i < len(b):
            h = b[i:i + 8]
            if len(h) < 8:
                if b[i] == 0:
                    break                   # pode ser começo de cabeçalho: espera o resto
                out.append(b[i]); i += 1; continue
            echo = h[0:4] == bytes([0, 0, 0, n]) and h[6:8] in RX_CMDS  # eco "00 00 00 0N"
            if not (valid_header(h) or echo):
                out.append(b[i]); i += 1    # byte solto (ex.: 00 extra do f0fd): segue cru
                continue
            if echo and not valid_header(h):
                # eco de comando ("00 00 00 0N 00 0b 40 1f ff 00"): o campo de tamanho
                # não bate com o frame real -> descarta até o próximo cabeçalho válido
                j = next((k for k in range(i + 8, len(b) - 7) if valid_header(b[k:k + 8])), None)
                if j is None:
                    break                   # espera o próximo frame p/ achar o fim
                i = j
                continue
            L = (h[4] << 8) | h[5]
            total = L if (h[6:8] == b"\x0b\x4a" and L == 0xa4) else 7 + L
            if len(b) - i < total:
                break                       # frame incompleto: espera
            if h[1] != n:                   # frame de outra sessão (nuvem/app): repassa
                out += b[i:i + total]
            i += total
        self.fwd_buf = b[i:]
        return bytes(out)

    def proxy_c2u(self, conn, up):
        """central -> nuvem: encaminha (menos a nossa sessão) e TAPeia p/ o HA."""
        reason = "conexão fechada pela central"
        while self.sock is conn:
            try:
                data = conn.recv(4096)
            except OSError as e:
                reason = f"erro de conexão: {e.__class__.__name__}"
                break
            if not data:
                break
            if self.sock is not conn:
                return
            if up:
                try:
                    fwd = self._c2u_filter(data)
                    if fwd:
                        up.sendall(fwd)          # repassa p/ a nuvem (app segue vivo)
                except OSError:
                    print("[proxy] upstream (nuvem) caiu — controle local segue")
                    up = None
            self.tap_buf += data
            frames, self.tap_buf = split_frames(self.tap_buf)
            for cmd, frame in frames:
                self.tap(frame, cmd)
        self.drop(conn, reason)

    def proxy_u2c(self, conn, up):
        """nuvem -> central: encaminha CRU."""
        while self.sock is conn:
            try:
                data = up.recv(4096)
            except OSError:
                break
            if not data:
                print("[proxy] nuvem encerrou a conexão")
                break
            try:
                conn.sendall(data)
            except OSError:
                break


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
            if name == "status":
                relay.send(relay.my_sid, CMD_MAP["status"]); self._send(200, "ok", "text/plain")
            elif name in CMD_MAP:
                relay.control(CMD_MAP[name]); self._send(200, "ok", "text/plain")
            else:
                self._send(404, "comando desconhecido", "text/plain")
    # bind em localhost: o painel aciona a cerca; não exponha na rede sem auth
    httpd = HTTPServer(("127.0.0.1", port), H)
    print(f"[web] painel em http://127.0.0.1:{port}  (só local; aciona a cerca)")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

def main():
    builtins.print = _ts_print          # horário em todas as linhas do log (relay e MQTT)
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="0.0.0.0:9009")
    ap.add_argument("--poll", type=int, default=15)
    ap.add_argument("--keepalive", type=int, default=0, help="(ignorado) f0f1 é DISCONNECT, nunca é enviado; sessão mantida via resposta ao f0f7 + polls")
    ap.add_argument("--web", type=int, default=0, help="porta do painel web (0 = desligado)")
    ap.add_argument("--session-hex", default=SESSION_OPEN_HEX,
                    help="payload da abertura de sessão de controle (hex); padrão = o da nuvem real")
    ap.add_argument("--code", default="", help="(ignorado) a central não autentica o servidor; mantido p/ compatibilidade")
    ap.add_argument("--mqtt", default="", help="broker MQTT p/ Home Assistant: host[:porta] (porta padrão 1883)")
    ap.add_argument("--mqtt-user", default=None)
    ap.add_argument("--mqtt-pass", default=None,
                    help="senha do broker (ou variável de ambiente MQTT_PASSWORD, que não aparece no ps)")
    ap.add_argument("--mqtt-node", default="elc6012net", help="id do dispositivo no HA")
    ap.add_argument("--upstream", default="", help="[EXPERIMENTAL] modo proxy/híbrido: "
                    "IP da nuvem (host[:porta]); repassa o tráfego à Intelbras e injeta os "
                    "comandos locais numa sessão própria")
    ap.add_argument("--inject-session", type=int, default=2, choices=range(1, 16), metavar="1-15",
                    help="[EXPERIMENTAL] índice da sessão usada p/ os comandos locais no modo proxy. "
                    "A nuvem dá um índice por cliente (ponte de nuvem=1, app=2…): use um livre.")
    ap.add_argument("--mqtt-name", default="Intelbras ELC 6012 NET", help="nome do dispositivo no HA")
    ap.add_argument("--tz", default=os.environ.get("TZ", ""),
                    help="fuso da hora enviada à central, ex.: America/Sao_Paulo (padrão: env TZ ou hora local)")
    ap.add_argument("--daemon", action="store_true",
                    help="sem terminal interativo (serviço/App do HA): não lê comandos do stdin")
    ns = ap.parse_args()
    set_tz(ns.tz)
    if ns.mqtt_pass is None:
        ns.mqtt_pass = os.environ.get("MQTT_PASSWORD")
    host, port = ns.listen.rsplit(":", 1)
    r = Relay()
    r.session_open = bytes.fromhex(ns.session_hex.replace(" ", ""))
    if ns.upstream:
        uh, _, up_ = ns.upstream.partition(":")
        r.proxy = True
        r.upstream = (uh, int(up_ or 9009))
        r.inject_sid = bytes([0, 0, 0, ns.inject_session])
        print(f"[proxy] modo híbrido (EXPERIMENTAL): repassando p/ a nuvem {r.upstream[0]}:{r.upstream[1]}")
        print("[proxy] a central fala com a nuvem (app/avisos seguem) e o relay injeta comandos locais.")
    if ns.code:
        print("[i] --code é ignorado: a sessão de controle não usa o código (a central não autentica o servidor).")
    if ns.mqtt:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mqtt_bridge import MqttBridge
        mh, _, mp = ns.mqtt.partition(":")
        r.mqtt = MqttBridge(r, mh, int(mp or 1883), ns.mqtt_user, ns.mqtt_pass, ns.mqtt_node,
                            name=ns.mqtt_name)
        r.mqtt.start()
    if ns.web:
        start_web(r, ns.web)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, int(port))); srv.listen(1)
    print(f"relay local escutando em {host}:{port}. Aguardando a central...")
    print("comandos: arm disarm shockon shockoff allon alloff status | "
          "panic [0-3] sirenoff | pgm <1|2> <on|off> | bypass <8 digitos> | "
          "events | raw <hex> | quit")

    def accept_loop():
        while True:
            conn, addr = srv.accept()
            print(f"== central conectou de {addr}")
            if not r.proxy:   # no híbrido quem consulta é a nuvem: sem timeout de ociosidade
                conn.settimeout(max(IDLE_TIMEOUT_MIN, 4 * ns.poll))   # detecta conexão morta
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # reset de estado por conexão (a central reconecta sozinha no churn de WiFi):
            # sem isso, buf/sessão/threads antigas vazam e dessincronizam.
            with r.lock:
                old, oldup = r.sock, r.up
                r.sock = conn
                r.buf = b""; r.tap_buf = b""; r.fwd_buf = b""
                r.session_opened = False
                r._last_status_key = None
                r._pending_cmd = None
                r.up = None
                r._sess_code = None
                r._sess_reset_done = False
                r._reset_ok_logged = False
            for s in (old, oldup):
                if s:
                    try: s.close()
                    except OSError: pass
            if r.mqtt: r.mqtt.set_available(True)
            if r.proxy:
                # abre a conexão com a nuvem real e vira um túnel central<->nuvem,
                # tapeando o tráfego e injetando comandos localmente.
                try:
                    up = socket.create_connection(r.upstream, timeout=10)
                except OSError as e:
                    print(f"[proxy] não conectou na nuvem {r.upstream}: {e} — seguindo só local")
                    up = None
                r.up = up
                threading.Thread(target=r.proxy_c2u, args=(conn, up), daemon=True).start()
                if up:
                    threading.Thread(target=r.proxy_u2c, args=(conn, up), daemon=True).start()
            else:
                threading.Thread(target=r.reader, args=(conn,), daemon=True).start()
                threading.Thread(target=r.poller, args=(conn, ns.poll), daemon=True).start()
    threading.Thread(target=accept_loop, daemon=True).start()

    def shutdown(*_):
        # encerra a sessão de controle ao parar: sem isso ela fica presa na central e a
        # próxima conexão recebe sessão só de leitura (código 0x01)
        if r.sock and r.session_opened:
            print("[SESSAO] encerrando a sessão (f0 f1) antes de sair")
            r.send(r.my_sid, bytes.fromhex("f0f1"), quiet=True)   # no híbrido, só a sessão injetada
            time.sleep(0.3)
        os._exit(0)
    signal.signal(signal.SIGTERM, shutdown)

    if ns.daemon:                      # serviço: sem stdin, só fica rodando
        threading.Event().wait()
    for line in sys.stdin:
        cmd = line.strip().lower()
        if cmd == "quit": break
        elif cmd == "status":
            r.send(r.my_sid, CMD_MAP["status"])           # leitura: não precisa reabrir sessão
        elif cmd in CMD_MAP:                             # arme/desarme/choque: comando de controle
            r.control(CMD_MAP[cmd])
        elif cmd == "panic" or cmd.startswith("panic "):
            # 40 1a <tipo>: 0=silencioso, 1=audível; 2=fogo e 3=médico são recusados no ELC.
            pr = cmd.split()
            tipo = int(pr[1]) if len(pr) == 2 and pr[1] in ("0","1","2","3") else 1
            print(f"[!] PÂNICO tipo={tipo} ({'silencioso' if tipo==0 else 'audivel' if tipo==1 else 'fogo' if tipo==2 else 'medico'})")
            r.control(bytes.fromhex("401a") + bytes([tipo]))
        elif cmd == "sirenoff":
            # 40 19 = desliga a sirene sem desarmar (aceito pela central; efeito não verificado)
            print("[*] desligar sirene (40 19)")
            r.control(bytes.fromhex("4019"))
        elif cmd.startswith("pgm "):   # pgm <1|2> <on|off>
            pr = cmd.split()
            if len(pr) == 3 and pr[1] in ("1","2") and pr[2] in ("on","off"):
                r.control(bytes.fromhex("45af") + bytes([int(pr[1])-1, 1 if pr[2]=="on" else 0]))  # PGM base-0
            else:
                print("uso: pgm <1|2> <on|off>")
        elif cmd == "events":
            for pg in range(8):
                r.send(r.my_sid, bytes.fromhex("3900")+bytes([pg]))
        elif cmd.startswith("bypass "):
            z = cmd.split()[1]  # 8 dígitos 0/1, ex.: bypass 00100000 (zona 3)
            if len(z) == 8 and set(z) <= {"0","1"}:
                r.control(bytes.fromhex("401fff") + bytes(int(c) for c in z))
            else:
                print("uso: bypass <8 dígitos 0/1>, ex.: bypass 00100000")
        elif cmd.startswith("raw "):
            r.send(r.my_sid, bytes.fromhex(cmd[4:].replace(" ", "")))
        elif cmd:
            print("comando desconhecido")

if __name__ == "__main__":
    main()
