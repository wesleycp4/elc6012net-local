#!/usr/bin/env python3
"""Troca o servidor da nuvem Intelbras na flash do módulo Wi-Fi (ESP8266) por um
endereço local, corrigindo o checksum (XOR, semente 0xEF) e o SHA256 anexado de
cada slot de OTA. Só mexe nas strings de host; nada mais da imagem muda.

Uso:
  patch_server.py dump.bin saida.bin --novo elc.seudominio.com
Opções:
  --so-nacional        troca só 'amt8000...' (padrão: troca também 'global.amt8000...')
  --bloquear-ota       aponta amtupdate + o IP fixo dele para endereço morto
                       (evita que uma atualização da Intelbras desfaça o patch)
"""
import argparse
import hashlib
import struct
import sys

HOSTS = [b"global.amt8000.intelbras.com.br", b"amt8000.intelbras.com.br"]
OTA_HOST = b"amtupdate.intelbras.com.br"
OTA_IP   = b"54.207.162.243"

def seg_checksum_pos(d, base):
    assert d[base] == 0xE9, f"sem cabeçalho 0xE9 em 0x{base:x}"
    nseg = d[base+1]; off = base+8; segs = []
    for _ in range(nseg):
        load, ln = struct.unpack("<II", d[off:off+8]); off += 8
        segs.append((off, ln)); off += ln
    cks = base + ((off-base+15)//16)*16 - 1
    return segs, cks

def recompute(d, base):
    segs, cks = seg_checksum_pos(d, base)
    chk = 0xEF
    for o, ln in segs:
        for b in d[o:o+ln]: chk ^= b
    d[cks] = chk & 0xFF
    sha = hashlib.sha256(bytes(d[base:cks+1])).digest()
    d[cks+1:cks+33] = sha
    return cks

def verify(d, base):
    segs, cks = seg_checksum_pos(d, base)
    chk = 0xEF
    for o, ln in segs:
        for b in d[o:o+ln]: chk ^= b
    ok_c = (chk & 0xFF) == d[cks]
    ok_h = hashlib.sha256(bytes(d[base:cks+1])).digest() == d[cks+1:cks+33]
    return ok_c, ok_h

def find_app_bases(d):
    """Lê a tabela de partições (@0x8000) e devolve os offsets das partições app."""
    bases = []
    off = 0x8000
    while d[off:off+2] == b"\xaa\x50":
        t = d[off+2]; addr = struct.unpack("<I", d[off+4:off+8])[0]
        if t == 0 and d[addr] == 0xE9:   # app com imagem válida
            bases.append(addr)
        off += 32
    if not bases:  # fallback: varre 0xE9 em limites de 4KB com entry em irom
        for b in range(0, len(d), 0x1000):
            if d[b] == 0xE9 and b >= 0x10000:
                bases.append(b)
    return bases

def replace_cstr(d, target, newbytes, base, size):
    """Troca a C-string 'target' (delimitada por \\0 antes e depois) dentro de
    [base, base+size). Retorna lista de offsets trocados."""
    hits = []
    i = base
    end = base + size
    tl = len(target)
    while True:
        j = d.find(target, i, end)
        if j < 0: break
        i = j + 1
        if j > 0 and d[j-1] != 0:          # não é começo de string
            continue
        if d[j+tl] != 0:                   # não termina em \0 (é prefixo de outra)
            continue
        assert len(newbytes) <= tl, f"'{newbytes}' é maior que '{target}' ({len(newbytes)}>{tl})"
        d[j:j+tl+1] = newbytes + b"\x00" + b"\x00"*(tl-len(newbytes))
        hits.append(j)
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada"); ap.add_argument("saida")
    ap.add_argument("--novo", required=True, help="novo host/IP (<= 24 caracteres)")
    ap.add_argument("--so-nacional", action="store_true")
    ap.add_argument("--bloquear-ota", action="store_true")
    ap.add_argument("--ota-morto", default="127.0.0.1")
    ns = ap.parse_args()

    d = bytearray(open(ns.entrada, "rb").read())
    new = ns.novo.encode()
    targets = HOSTS[1:] if ns.so_nacional else HOSTS
    if len(new) > max(len(t) for t in targets):
        sys.exit(f"'{ns.novo}' não cabe (máx {max(len(t) for t in targets)} p/ os alvos escolhidos)")

    bases = find_app_bases(d)
    print(f"Partições app encontradas: {[hex(b) for b in bases]}")
    total = 0
    for base in bases:
        _, cks = seg_checksum_pos(d, base)
        okc, okh = verify(d, base)
        assert okc and okh, f"imagem @0x{base:x} não confere ANTES do patch (checksum={okc} sha={okh})"
        size = (cks+33) - base + 0x1000
        for t in targets:
            if len(new) > len(t):   # pula alvo curto demais p/ esse host
                continue
            hits = replace_cstr(d, t, new, base, size)
            for h in hits:
                print(f"  @0x{base:x}: '{t.decode()}' -> '{ns.novo}' em 0x{h:x}")
                total += 1
        if ns.bloquear_ota:
            for t in (OTA_HOST, OTA_IP):
                dead = ns.ota_morto.encode()
                if len(dead) <= len(t):
                    for h in replace_cstr(d, t, dead, base, size):
                        print(f"  @0x{base:x}: OTA '{t.decode()}' -> '{ns.ota_morto}' em 0x{h:x}")
                        total += 1
        recompute(d, base)
        okc, okh = verify(d, base)
        assert okc and okh, f"falha ao recalcular @0x{base:x}"
        print(f"  @0x{base:x}: checksum+SHA256 recalculados OK")
    open(ns.saida, "wb").write(d)
    print(f"\n{total} string(s) trocada(s). Gravado: {ns.saida}")

if __name__ == "__main__":
    main()
