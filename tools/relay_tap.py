#!/usr/bin/env python3
"""
relay_tap.py — proxy transparente com log, para engenharia reversa do
caminho central <-> nuvem do ELC 6012 NET (e afins). Stdlib pura.

Uso legítimo: no SEU equipamento, na SUA rede. A central continua
funcionando normalmente (o tráfego é reencaminhado para a nuvem real);
este proxy apenas registra, em claro, os bytes das duas direções.

Pré-requisitos:
  - Descobrir o IP REAL da nuvem (sem o override de DNS):
        nslookup amt8000.intelbras.com.br 8.8.8.8
  - Redirecionar, na sua rede, o hostname da nuvem para a máquina que
    roda este proxy (DNS local: Pi-hole/AdGuard/dnsmasq; ou DNAT no
    roteador). O proxy NÃO deve resolver o hostname para si mesmo:
    passe o IP real em --upstream para evitar loop.

Exemplo:
    python3 relay_tap.py --listen 0.0.0.0:9009 \
        --upstream 200.0.0.0:9009 --log captura_amt8000.log

Rode uma instância por hostname (amt e amt8000), em IPs/portas distintos,
cada uma apontando para o IP real correspondente.

Reversível: pare o proxy e remova o override de DNS -> volta ao normal.
Se o proxy cair, a central perde a nuvem até você remover o override,
então faça isso com essa ciência.
"""
import argparse, asyncio, sys
from datetime import datetime


def hexdump(data: bytes, width: int = 16) -> str:
    out = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        h = " ".join(f"{b:02x}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"    {i:04x}  {h:<{width*3}}  {a}")
    return "\n".join(out)


class Tap:
    def __init__(self, logpath):
        self.logfile = open(logpath, "a", buffering=1, encoding="utf-8") if logpath else None
        self.n = 0

    def log(self, conn_id, direction, data):
        ts = datetime.now().isoformat(timespec="milliseconds")
        header = f"[{ts}] conn#{conn_id} {direction} {len(data)}B"
        block = header + "\n" + hexdump(data)
        print(block, flush=True)
        if self.logfile:
            self.logfile.write(block + "\n")

    async def pump(self, conn_id, direction, reader, writer):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                self.log(conn_id, direction, data)
                writer.write(data)
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def handle(self, up_host, up_port, local_reader, local_writer):
        self.n += 1
        conn_id = self.n
        peer = local_writer.get_extra_info("peername")
        print(f"== conn#{conn_id} de {peer} -> {up_host}:{up_port}", flush=True)
        try:
            up_reader, up_writer = await asyncio.open_connection(up_host, up_port)
        except OSError as e:
            print(f"!! conn#{conn_id}: upstream falhou: {e}", flush=True)
            local_writer.close()
            return
        await asyncio.gather(
            self.pump(conn_id, "C->S", local_reader, up_writer),   # central -> nuvem
            self.pump(conn_id, "S->C", up_reader, local_writer),   # nuvem -> central
        )
        print(f"== conn#{conn_id} encerrada", flush=True)


async def main():
    ap = argparse.ArgumentParser(description="Proxy transparente com log (TCP)")
    ap.add_argument("--listen", required=True, help="IP:porta onde escutar (ex.: 0.0.0.0:9009)")
    ap.add_argument("--upstream", required=True, help="IP:porta REAL da nuvem (use IP, não hostname)")
    ap.add_argument("--log", default=None, help="arquivo de log (opcional; além do stdout)")
    ns = ap.parse_args()
    lh, lp = ns.listen.rsplit(":", 1)
    uh, up = ns.upstream.rsplit(":", 1)
    tap = Tap(ns.log)
    server = await asyncio.start_server(
        lambda r, w: tap.handle(uh, int(up), r, w), lh, int(lp))
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"escutando em {addrs}; upstream {uh}:{up}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
