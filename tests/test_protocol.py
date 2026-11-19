import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "relay"))
import elc_local_relay as m  # noqa: E402


class FramingTest(unittest.TestCase):
    def test_build_matches_capture(self):
        # PROTOCOL.md §2: comando choque ON capturado da nuvem
        self.assertEqual(m.build(b"\0\0\0\1", bytes.fromhex("401e0201")).hex(" "),
                         "00 00 00 01 00 04 40 1e 02 01 a7")
        self.assertEqual(m.build(b"\0\0\0\1", bytes.fromhex("0b4a")).hex(" "),
                         "00 00 00 01 00 02 0b 4a bd")

    def test_session_open_frame(self):
        self.assertEqual(m.build(b"\0\0\0\1", bytes.fromhex(m.SESSION_OPEN_HEX)).hex(" "),
                         "00 00 00 01 00 0b f0 f0 03 03 06 05 09 00 00 00 01 fe")

    def test_split_frames_resyncs_and_keeps_rest(self):
        st = bytearray(164)
        st[0:8] = bytes([0, 1, 0, 0, 0, 0xA4, 0x0B, 0x4A])
        ack = bytes.fromhex("0000000000 02 f0fe f3".replace(" ", ""))
        buf = b"\x00" + ack + bytes(st) + ack[:5]          # lixo + ack + status + parcial
        frames, rest = m.split_frames(buf)
        self.assertEqual([c.hex() for c, _ in frames], ["f0fe", "0b4a"])
        self.assertEqual(len(frames[1][1]), 164)
        self.assertEqual(rest, ack[:5])

    def test_time_sync_payload(self):
        p = m.time_sync_payload()
        self.assertEqual(p[:3], bytes.fromhex("f08026"))
        self.assertEqual(len(p), 9)


class StatusTest(unittest.TestCase):
    def frame(self, rssi):
        f = bytearray(164)
        f[0:8] = bytes([0, 1, 0, 0, 0, 0xA4, 0x0B, 0x4A])
        f[30], f[31], f[46], f[163] = 1, 0, 0b101, rssi
        f[72:78] = bytes([19, 11, 26, 12, 49, 29])
        return bytes(f)

    def test_rssi(self):
        self.assertEqual(m.rssi_dbm(self.frame(0xCF)), -49)
        self.assertIsNone(m.rssi_dbm(self.frame(0)))

    def test_decode_status(self):
        s = m.decode_status(self.frame(0xCF))
        self.assertIn("choque=ON", s)
        self.assertIn("alarme=off", s)
        self.assertIn("zonas=0500", s)
        self.assertIn("sinal=-49dBm", s)
        self.assertIn("relogio=19/11/26 12:49:29", s)
        self.assertIn("sinal=?", m.decode_status(self.frame(0)))


class HybridFilterTest(unittest.TestCase):
    def test_injected_session_not_forwarded(self):
        r = m.Relay()
        r.inject_sid = b"\0\0\0\2"
        ours = m.build(b"\0\2\0\0", bytes.fromhex("f0fd00"))
        cloud = m.build(b"\0\1\0\0", bytes.fromhex("f0fd00"))
        self.assertEqual(r._c2u_filter(ours + cloud), cloud)


if __name__ == "__main__":
    unittest.main()
