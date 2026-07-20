#!/usr/bin/env python3
# scripts/il2cpp_patch.py — Patchea funciones ARM64 en libil2cpp.so por RVA
# Uso: python3 il2cpp_patch.py libil2cpp.so <hex_rva> --ret1 [--dry]
import sys
import os
import struct
import argparse

ARM64_RET1 = bytes.fromhex("20 00 80 52 C0 03 5F D6".replace(" ",""))

def main():
    parser = argparse.ArgumentParser(description="Patch libil2cpp.so ARM64 functions")
    parser.add_argument("sofile", help="Output file to patch (in-place) or read")
    parser.add_argument("rva", help="RVA/offset hexadecimal (e.g. 0x1A2B3C0)")
    parser.add_argument("--ret1", action="store_true", help="Patch with MOV W0,#1; RET")
    parser.add_argument("--dry", action="store_true", help="Don't write, only show")
    parser.add_argument("--bytes", help="Custom hex bytes to write (space-separated)")
    args = parser.parse_args()
    
    offset = int(args.rva, 16)
    with open(args.sofile, "rb") as f:
        data = bytearray(f.read())
    
    if args.ret1:
        patch = ARM64_RET1
        print(f"[PATCH] RVA=0x{offset:08x} → RET1 ({patch.hex()})")
    elif args.bytes:
        patch = bytes.fromhex(args.bytes.replace(" ",""))
        print(f"[PATCH] RVA=0x{offset:08x} → custom bytes ({patch.hex()})")
    else:
        print("ERROR: especifica --ret1 o --bytes")
        sys.exit(1)
    
    if offset + len(patch) > len(data):
        print(f"ERROR: Offset 0x{offset:x} excede tamaño del archivo ({len(data)})")
        sys.exit(1)
    
    old = data[offset:offset+len(patch)]
    print(f"[PATCH] Old bytes: {old.hex()}")
    data[offset:offset+len(patch)] = patch
    print(f"[PATCH] New bytes: {data[offset:offset+len(patch)].hex()}")
    
    if not args.dry:
        with open(args.sofile, "wb") as f:
            f.write(data)
        print(f"[PATCH] ✓ Archivo escrito: {args.sofile}")
    else:
        print("[PATCH] --dry: NO se escribió nada")

if __name__ == '__main__':
    main()
