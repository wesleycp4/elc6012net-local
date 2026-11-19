"""Central falsa para testar o relay sem o equipamento.

Responde registro, hora, abertura de sessão e status como a central real (formatos
de PROTOCOL.md). `stale=True` simula a sessão presa de uma conexão anterior: a
primeira abertura responde `f0 f0 01` até receber `f0 f1`.
"""
import socket
import struct
import threading
import time

REG = bytes.fromhex("3f9400000080854400000035")


def frame(sess: bytes, payload: bytes) -> bytes:
    return sess + struct.pack(">H", len(payload)) + payload + b"\x00"


def status(choque: int, alarme: int, rssi_byte: int = 0xCF) -> bytes:
    f = bytearray(164)
    f[0:8] = bytes([0, 1, 0, 0, 0, 0xA4, 0x0B, 0x4A])
    f[30], f[31], f[163] = choque, alarme, rssi_byte
    return bytes(f)


class FakeCentral:
    def __init__(self, port: int, stale: bool = False, choque: int = 0, alarme: int = 0):
        self.state = {"choque": choque, "alarme": alarme}
        self.stale = stale
        self.control_ok = False
        self.received = b""
        self.answer_status = True
        self.sock = socket.create_connection(("127.0.0.1", port))
        self.sock.settimeout(0.2)
        self._stop = False
        self.sock.sendall(frame(b"\0\0\0\0", REG))
        self.sock.sendall(frame(b"\0\0\0\0", bytes.fromhex("f080")))
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop:
            try:
                d = self.sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not d:
                return
            self.received += d
            if bytes.fromhex("0002f0f1") in d:
                self.stale, self.control_ok = False, False
            if bytes.fromhex("f0f0030306") in d:
                code = 1 if self.stale else 0
                self.control_ok = code == 0
                self.sock.sendall(frame(b"\0\1\0\0", bytes([0xF0, 0xF0, code])))
            i = d.find(b"\x40\x1e")
            if i >= 0 and len(d) >= i + 4:
                part, val = d[i + 2], d[i + 3]
                keys = {1: ("alarme",), 2: ("choque",), 0xFF: ("alarme", "choque")}[part]
                if self.control_ok and any(self.state[k] != val for k in keys):
                    for k in keys:
                        self.state[k] = val
                    self.sock.sendall(frame(b"\0\1\0\0", bytes.fromhex("f0fd00")))
                else:
                    self.sock.sendall(frame(b"\0\1\0\0", bytes.fromhex("f0fd21")))
            if b"\x0b\x4a" in d and self.answer_status:
                self.sock.sendall(status(self.state["choque"], self.state["alarme"]))

    def reset(self):
        """Fecha com RST (como uma queda de Wi-Fi/conexão resetada)."""
        self._stop = True
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        self.sock.close()


def wait_for(cond, timeout=8.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(step)
    return False
