import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "relay"))
from mqtt_bridge import MqttBridge  # noqa: E402


class FakeClient:
    def __init__(self):
        self.pub = {}

    def publish(self, topic, payload, qos=0, retain=False):
        self.pub[topic] = payload


class FakeRelay:
    sock = None
    last_status = {}


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.b = MqttBridge(FakeRelay(), "localhost", node="t")
        self.b.cli = FakeClient()
        self.b._connected = True

    def test_state_json(self):
        st = {"choque": True, "alarme": False, "zonas": "0500", "disparo": "0000", "sinal": -50}
        out = MqttBridge._state_json(st)
        self.assertEqual(out["choque"], True)
        self.assertEqual(out["disparo"], False)
        self.assertEqual([out[f"zona{n}"] for n in range(1, 9)],
                         [True, False, True, False, False, False, False, False])
        self.assertEqual(out["sinal"], -50)

    def test_discovery(self):
        self.b._publish_discovery()
        topics = set(self.b.cli.pub)
        self.assertIn("homeassistant/switch/t/cerca/config", topics)
        self.assertIn("homeassistant/sensor/t/sinal/config", topics)
        self.assertEqual(len([t for t in topics if "/zona" in t]), 8)
        alarm = json.loads(self.b.cli.pub["homeassistant/alarm_control_panel/t/alarme/config"])
        self.assertEqual(alarm["supported_features"], ["arm_away"])
        for cfg in map(json.loads, self.b.cli.pub.values()):
            self.assertEqual(cfg["availability_topic"], "elc6012/t/availability")
            self.assertTrue(cfg["unique_id"].startswith("elc6012_t_"))


if __name__ == "__main__":
    unittest.main()
