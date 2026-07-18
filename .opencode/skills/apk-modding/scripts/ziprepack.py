#!/usr/bin/env python3
"""
Repack an APK with correct compression rules and optional DEX replacements.

Rules:
  - STORE (no compression) for:
      * all classes*.dex
      * resources.arsc
      * lib/** (all .so)
  - DEFLATE for the rest
  - Remove only signature files in META-INF/ (.SF, .RSA, .DSA, .EC, MANIFEST.MF)
  - Preserve META-INF/services/* and any other service descriptors

Usage:
  python3 ziprepack.py --in app.apk --out hacked.apk \
    --replace classes2.dex=classes2_new.dex classes8.dex=classes8_new.dex

Notes:
  - Use zipalign and apksigner afterwards (see strip_sign_and_sign.py)
"""

from __future__ import annotations
import argparse
import os
import sys
import zipfile

SIG_EXTS = {'.SF', '.RSA', '.DSA', '.EC'}
SIG_BASENAMES = {'MANIFEST.MF'}


def should_store(name: str) -> bool:
    n = name.lower()
    if n.endswith('.dex'):
        return True
    if n.endswith('.arsc') and n.endswith('resources.arsc'):
        return True
    if n.startswith('lib/') and n.endswith('.so'):
        return True
    return False


def is_sig_file(name: str) -> bool:
    if not name.upper().startswith('META-INF/'):
        return False
    base = os.path.basename(name)
    ext = os.path.splitext(base)[1].upper()
    return (ext in SIG_EXTS) or (base.upper() in SIG_BASENAMES)


def load_replacements(pairs: list[str]) -> dict[str, bytes]:
    mapping: dict[str, bytes] = {}
    for pair in pairs or []:
        if '=' not in pair:
            print(f'Formato inválido en --replace: {pair}. Use destino=origen', file=sys.stderr)
            sys.exit(2)
        dest, src = pair.split('=', 1)
        dest = dest.strip()
        src = src.strip()
        with open(src, 'rb') as f:
            mapping[dest] = f.read()
    return mapping


def repack(src_apk: str, out_apk: str, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(src_apk, 'r') as zin:
        with zipfile.ZipFile(out_apk, 'w', compression=zipfile.ZIP_STORED, allowZip64=True, strict_timestamps=False) as zout:
            for item in zin.infolist():
                name = item.filename
                if is_sig_file(name):
                    continue
                if name in replacements:
                    data = replacements[name]
                else:
                    data = zin.read(name)
                comp = zipfile.ZIP_STORED if should_store(name) else zipfile.ZIP_DEFLATED
                zi = zipfile.ZipInfo(filename=name, date_time=item.date_time)
                zi.external_attr = item.external_attr
                zi.create_system = item.create_system
                zout.writestr(zi, data, compress_type=comp)


def main():
    ap = argparse.ArgumentParser(description='Reempaqueta un APK con reglas de compresión correctas y reemplazos opcionales')
    ap.add_argument('--in', dest='inp', required=True, help='APK de entrada')
    ap.add_argument('--out', dest='out', required=True, help='APK de salida')
    ap.add_argument('--replace', nargs='*', help='Pares destino=origen para reemplazos (p.ej. classes2.dex=classes2_new.dex)')
    args = ap.parse_args()

    repl = load_replacements(args.replace or [])
    repack(args.inp, args.out, repl)
    print(f'Generado: {args.out}')
    print('Siguiente: zipalign -p -f 4 hacked.apk hacked_aligned.apk && apksigner sign ...')


if __name__ == '__main__':
    main()
