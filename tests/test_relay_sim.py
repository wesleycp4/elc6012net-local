"""Relay inteiro contra uma central falsa (tests/_fake.py)."""
import socket
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "relay"))
import elc_local_relay as m  # noqa: E402

from tests._fake import FakeCentral, wait_for  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class RelaySimTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m.IDLE_TIMEOUT_MIN = 3
        cls.port = free_port()
        holder = {}
        orig = m.Relay.__init__

        def init(self):
            orig(self)
            holder["r"] = self
        m.Relay.__init__ = init
        sys.argv = ["relay", "--listen", f"127.0.0.1:{cls.port}", "--poll", "1", "--daemon"]
        threading.Thread(target=m.main, daemon=True).start()
        assert wait_for(lambda: "r" in holder)
        cls.r = holder["r"]
        time.sleep(0.3)

    def connect(self, **kw):
        c = FakeCentral(self.port, **kw)
        self.assertTrue(wait_for(lambda: self.r.session_opened and self.r.last_status))
        return c

    def test_1_command_and_redundant_skip(self):
        c = self.connect(choque=0)
        self.r.control(m.CMD_MAP["shockon"])
        self.assertTrue(wait_for(lambda: c.state["choque"] == 1))
        self.assertTrue(wait_for(lambda: self.r.last_status.get("choque") is True))
        sent = c.received.count(b"\x40\x1e\x02\x01")
        self.r.control(m.CMD_MAP["shockon"])            # já ligado: não envia
        time.sleep(0.5)
        self.assertEqual(c.received.count(b"\x40\x1e\x02\x01"), sent)
        c.reset()
        self.assertTrue(wait_for(lambda: self.r.sock is None))

    def test_2_stale_session_is_released(self):
        c = self.connect(stale=True, choque=0)
        self.assertTrue(wait_for(lambda: c.control_ok))   # f0 f1 + f0 f0 -> código 00
        self.r.control(m.CMD_MAP["shockon"])
        self.assertTrue(wait_for(lambda: c.state["choque"] == 1))
        c.reset()
        self.assertTrue(wait_for(lambda: self.r.sock is None))

    def test_3_probe_does_not_kick_central(self):
        m.HANDSHAKE_TIMEOUT = 1.0
        c = self.connect()
        central_sock = self.r.sock
        silent = socket.create_connection(("127.0.0.1", self.port))     # verificação de saúde
        http = socket.create_connection(("127.0.0.1", self.port))
        http.sendall(b"GET / HTTP/1.0\r\n\r\n")                       # varredura/curioso
        time.sleep(2.0)
        self.assertIs(self.r.sock, central_sock)
        silent.close(); http.close()
        c.reset()
        self.assertTrue(wait_for(lambda: self.r.sock is None))

    def test_4_idle_connection_dropped(self):
        c = self.connect()
        c.answer_status = False                          # central "some" sem fechar
        self.assertTrue(wait_for(lambda: self.r.sock is None, timeout=10))
        c.reset()


class ShutdownTest(unittest.TestCase):
    def test_sigterm_closes_session(self):
        port = free_port()
        p = subprocess.Popen([sys.executable, "-u", str(ROOT / "relay" / "elc_local_relay.py"),
                              "--listen", f"127.0.0.1:{port}", "--daemon"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.8)
            c = FakeCentral(port)
            self.assertTrue(wait_for(lambda: c.control_ok))
            p.terminate()
            self.assertEqual(p.wait(timeout=5), 0)
            self.assertTrue(wait_for(lambda: bytes.fromhex("0002f0f1") in c.received, timeout=3))
        finally:
            if p.poll() is None:
                p.kill()


if __name__ == "__main__":
    unittest.main()
