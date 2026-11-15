"""Ponte MQTT → Home Assistant para o relay do ELC 6012 NET.

Publica as entidades via MQTT Discovery (o HA cria sozinho), publica o estado
quando a central muda e assina os tópicos de comando → `relay.control(...)`.
Tudo LOCAL: central → relay → broker MQTT → HA, sem nuvem e sem internet.

Entidades criadas:
  - switch      "Cerca"   (choque on/off)          -> 40 1e 02 01 / 00
  - alarm_panel "Alarme"  (armar/desarmar/disparo) -> 40 1e 01 01 / 00
  - binary_sensor "Disparo"
  - binary_sensor "Zona 1..8"  (mapeamento de bit a confirmar)

Requer `paho-mqtt` (pip install paho-mqtt).
"""
import json

# comandos de controle (payload após a sessão) — mesmos bytes do relay
CMD = {
    "cerca_on":  bytes.fromhex("401e0201"),
    "cerca_off": bytes.fromhex("401e0200"),
    "arm":       bytes.fromhex("401e0101"),
    "disarm":    bytes.fromhex("401e0100"),
}


class MqttBridge:
    def __init__(self, relay, host, port=1883, user=None, password=None,
                 node="elc6012net", discovery_prefix="homeassistant",
                 name="Intelbras ELC 6012 NET"):
        self.relay = relay
        self.name = name                       # nome do dispositivo no HA
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.node = node                       # id único do dispositivo no HA
        self.dp = discovery_prefix
        self.base = f"elc6012/{node}"
        self.avail_t = f"{self.base}/availability"
        self.state_t = f"{self.base}/state"
        self.cli = None
        self._connected = False

    # --- tópicos ---
    def _cmd_t(self, obj):  return f"{self.base}/{obj}/set"
    def _cfg_t(self, comp, obj): return f"{self.dp}/{comp}/{self.node}/{obj}/config"

    @property
    def _device(self):
        return {"identifiers": [f"elc6012_{self.node}"],
                "name": self.name,
                "manufacturer": "Intelbras", "model": "ELC 6012 NET"}

    def start(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[mqtt] paho-mqtt não instalado. Rode: pip install paho-mqtt")
            return False
        # paho 2.0+ exige CallbackAPIVersion como 1o argumento; 1.x não tem.
        try:
            self.cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,
                                   client_id=f"elc6012-relay-{self.node}")
        except (AttributeError, TypeError):
            self.cli = mqtt.Client(client_id=f"elc6012-relay-{self.node}")  # paho 1.x
        if self.user:
            self.cli.username_pw_set(self.user, self.password or "")
        self.cli.will_set(self.avail_t, "offline", qos=1, retain=True)
        self.cli.on_connect = self._on_connect
        self.cli.on_message = self._on_message
        try:
            self.cli.connect(self.host, self.port, keepalive=30)
        except OSError as e:
            print(f"[mqtt] não conectou em {self.host}:{self.port}: {e}")
            return False
        self.cli.loop_start()
        print(f"[mqtt] conectando em {self.host}:{self.port} (node {self.node})")
        return True

    def _on_connect(self, cli, userdata, flags, rc, *a):
        if rc != 0:
            print(f"[mqtt] conexão recusada (rc={rc})"); return
        self._connected = True
        self._publish_discovery()
        # online só se a central já estiver conectada ao relay (num App o broker
        # sobe antes da central conectar)
        cli.publish(self.avail_t, "online" if self.relay.sock else "offline", qos=1, retain=True)
        for obj in ("cerca", "alarme"):
            cli.subscribe(self._cmd_t(obj), qos=1)
        print("[mqtt] conectado; entidades publicadas e comandos assinados")
        if self.relay.last_status:
            self.publish_state(self.relay.last_status)

    def _ent(self, obj, name, extra):
        """Config de descoberta comum a todas as entidades."""
        d = {"name": name, "unique_id": f"elc6012_{self.node}_{obj}",
             "state_topic": self.state_t, "availability_topic": self.avail_t,
             "device": self._device}
        d.update(extra)
        return d

    def _publish_discovery(self):
        def pub(comp, obj, cfg):
            self.cli.publish(self._cfg_t(comp, obj), json.dumps(cfg), qos=1, retain=True)
        pub("switch", "cerca", self._ent("cerca", "Cerca", {
            "command_topic": self._cmd_t("cerca"),
            "value_template": "{{ 'ON' if value_json.choque else 'OFF' }}",
            "payload_on": "ON", "payload_off": "OFF", "icon": "mdi:fence-electric"}))
        pub("alarm_control_panel", "alarme", self._ent("alarme", "Alarme", {
            "command_topic": self._cmd_t("alarme"),
            "value_template": ("{{ 'triggered' if value_json.disparo else "
                               "('armed_away' if value_json.alarme else 'disarmed') }}"),
            "payload_arm_away": "ARM_AWAY", "payload_disarm": "DISARM",
            "code_arm_required": False, "code_disarm_required": False}))
        pub("binary_sensor", "disparo", self._ent("disparo", "Disparo", {
            "device_class": "safety",
            "value_template": "{{ 'ON' if value_json.disparo else 'OFF' }}",
            "payload_on": "ON", "payload_off": "OFF"}))
        for n in range(1, 9):
            pub("binary_sensor", f"zona{n}", self._ent(f"zona{n}", f"Zona {n}", {
                "device_class": "door",
                "value_template": "{{ 'ON' if value_json.zona%d else 'OFF' }}" % n,
                "payload_on": "ON", "payload_off": "OFF"}))

    @staticmethod
    def _state_json(st):
        """Converte o last_status do relay no JSON que os templates leem."""
        zoncol = int(st.get("zonas", "0000")[:2] or "0", 16)   # 1o byte = zonas 1..8
        disparo = int(st.get("disparo", "0000") or "0", 16) != 0
        out = {"choque": bool(st.get("choque")), "alarme": bool(st.get("alarme")),
               "disparo": disparo}
        for n in range(1, 9):
            out[f"zona{n}"] = bool(zoncol >> (n - 1) & 1)
        return out

    def publish_state(self, st):
        if self.cli and self._connected:
            self.cli.publish(self.state_t, json.dumps(self._state_json(st)), qos=1, retain=True)

    def set_available(self, online):
        if self.cli and self._connected:
            self.cli.publish(self.avail_t, "online" if online else "offline", qos=1, retain=True)

    def _ctrl(self, key):
        # control() faz um sleep curto; dispara numa thread p/ não travar a rede do paho
        import threading
        threading.Thread(target=self.relay.control, args=(CMD[key],), daemon=True).start()

    def _on_message(self, cli, userdata, msg):
        payload = msg.payload.decode(errors="ignore").strip().upper()
        if msg.topic == self._cmd_t("cerca"):
            self._ctrl("cerca_on" if payload in ("ON", "1", "TRUE") else "cerca_off")
        elif msg.topic == self._cmd_t("alarme"):
            if payload == "DISARM":
                self._ctrl("disarm")
            elif payload in ("ARM_AWAY", "ARM_HOME", "ARM_NIGHT"):
                self._ctrl("arm")
        print(f"[mqtt] comando {msg.topic} = {payload}")
