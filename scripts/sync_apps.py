#!/usr/bin/env python3
"""Copia o código do relay (relay/*.py) para a pasta de cada App do Home Assistant.

O Supervisor monta a imagem só com a pasta do App, então o código precisa estar
lá dentro. `relay/` é a fonte; as cópias em `<app>/app/` não devem ser editadas.

    python3 scripts/sync_apps.py          # copia
    python3 scripts/sync_apps.py --check  # só confere (usado no CI)
"""
import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["elc_local_relay.py", "mqtt_bridge.py"]
APPS = ["elc6012net_local", "elc6012net_hibrido"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="só confere se as cópias estão iguais")
    ns = ap.parse_args()
    stale = []
    for app in APPS:
        dst = ROOT / app / "app"
        dst.mkdir(exist_ok=True)
        for f in FILES:
            src, out = ROOT / "relay" / f, dst / f
            if out.exists() and filecmp.cmp(src, out, shallow=False):
                continue
            stale.append(str(out.relative_to(ROOT)))
            if not ns.check:
                shutil.copy2(src, out)
    if ns.check and stale:
        print("Cópias desatualizadas (rode scripts/sync_apps.py):\n  " + "\n  ".join(stale))
        return 1
    print("ok" if not stale else "atualizado:\n  " + "\n  ".join(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
