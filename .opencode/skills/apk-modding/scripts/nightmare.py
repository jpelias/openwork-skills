#!/usr/bin/env python3
"""
nightmare.py — ARM64 binary patcher via hex pattern search & replace

Busca patrones de instrucciones ARM64 (en formato hex little-endian) dentro de
un binario (.so, .o, ejecutable) y reemplaza los bytes encontrados.

Útil para:
- Parchear instrucciones de salto (B, BL, RET) para bypassear checks
- Reemplazar constantes inmediatas (MOV, ADR, LDR)
- NOP-ear secuencias de instrucciones (0x00000000 = NOP en ARM64)

Uso:
    python3 nightmare.py <binary> <hex_pattern> <hex_replace> [--all] [--offset <hex>]

Ejemplos:
    # NOP-ear una instrucción en libapp.so (offset 0x3b24e0)
    python3 nightmare.py libapp.so "00009fa0" "00000000" --offset 0x3b24e0

    # Reemplazar MOV W0, #0x1 (0x52800020) con MOV W0, #0x0 (0x52800000)
    python3 nightmare.py libapp.so "20008052" "00008052"

    # Buscar y reemplazar TODAS las ocurrencias de un patrón
    python3 nightmare.py libapp.so "01000054" "00000014" --all
    # (cambia B.le a B (siempre salta) en todas las ocurrencias)

Notas:
- Los patrones son hex little-endian (como aparecen en el volcado binario)
- ARM64 es little-endian: la instrucción 0x52800020 se almacena como "20008052"
- Usar con precaución: un parche incorrecto corrompe el binario
- Siempre hacer backup antes de parchear
"""

import sys
import os
import re
import argparse
from pathlib import Path


def parse_hex_string(s: str) -> bytes:
    """Convierte string hex (con o sin 0x, espacios, o notación LE) a bytes."""
    s = s.strip().lower()
    if s.startswith('0x'):
        s = s[2:]
    # Eliminar espacios
    s = re.sub(r'\s+', '', s)
    if len(s) % 2 != 0:
        raise ValueError(f"Hex string length must be even, got: {s}")
    return bytes.fromhex(s)


def to_little_endian_hex(instruction: int, width: int = 4) -> str:
    """Convierte una instrucción ARM64 (int) a hex little-endian para buscar en binario."""
    return instruction.to_bytes(width, byteorder='little').hex()


def find_pattern(data: bytes, pattern: bytes, start_offset: int = 0) -> list:
    """Busca todas las ocurrencias de pattern en data. Retorna lista de offsets."""
    positions = []
    pos = data.find(pattern, start_offset)
    while pos != -1:
        positions.append(pos)
        pos = data.find(pattern, pos + 1)
    return positions


def patch_binary(input_path: str, output_path: str, pattern: bytes,
                 replacement: bytes, offset: int = -1, replace_all: bool = False) -> int:
    """
    Parchea el binario.
    - Si offset >= 0: parchea exactamente en esa posición.
    - Si offset < 0: busca pattern y parchea según replace_all.
    Retorna número de parches aplicados.
    """
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())

    patches_applied = 0

    if offset >= 0:
        # Parcheo en offset específico
        if offset + len(replacement) > len(data):
            raise ValueError(f"Offset 0x{offset:x} + replacement length exceeds file size")
        # Verificar que el patrón coincida (opcional, para seguridad)
        existing = data[offset:offset + len(pattern)]
        if existing != pattern:
            print(f"[!] Warning: bytes at offset 0x{offset:x} do not match pattern")
            print(f"    Expected: {pattern.hex()}")
            print(f"    Found:    {existing.hex()}")
            resp = input("Continue anyway? (y/N): ")
            if resp.lower() != 'y':
                print("Aborted.")
                sys.exit(1)
        data[offset:offset + len(replacement)] = replacement
        patches_applied = 1
        print(f"[+] Patched at offset 0x{offset:x}")
    else:
        # Búsqueda de patrón
        positions = find_pattern(data, pattern)
        if not positions:
            print(f"[-] Pattern {pattern.hex()} not found in {input_path}")
            return 0
        print(f"[+] Found {len(positions)} occurrence(s) of pattern {pattern.hex()}:")
        for pos in positions:
            print(f"    0x{pos:x}  (file offset)  /  0x{pos:x}  (relative)")

        if not replace_all and len(positions) > 1:
            print(f"\n[!] Multiple matches found. Use --all to patch all, or --offset <hex> for specific.")
            resp = input("Patch the first match? (y/N): ")
            if resp.lower() != 'y':
                print("Aborted.")
                sys.exit(1)
            positions = positions[:1]

        for pos in positions:
            data[pos:pos + len(replacement)] = replacement
            patches_applied += 1
            print(f"[+] Patched at 0x{pos:x}")

    # Escribir output
    out = output_path if output_path else input_path
    with open(out, 'wb') as f:
        f.write(data)
    print(f"[+] Output written to: {out}")
    return patches_applied


def print_disassembly_hint(offset: int, file_path: str):
    """Sugiere comandos para verificar el parche con radare2 o objdump."""
    print(f"\n[?] To verify patch, disassemble around offset 0x{offset:x}:")
    print(f"    r2 -A -c 'pd 20 @ 0x{offset:x}' {file_path}")
    print(f"    aarch64-linux-gnu-objdump -d {file_path} | grep -A 5 -B 5 \"{offset:x}\"")


def main():
    parser = argparse.ArgumentParser(
        description="ARM64 binary patcher via hex pattern search & replace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # NOP-ear una instrucción (offset conocido)
  %(prog)s libapp.so 00009fa0 00000000 --offset 0x3b24e0

  # Cambiar MOV W0, #0x1 a MOV W0, #0x0 (todas las ocurrencias)
  %(prog)s libapp.so 20008052 00008052 --all

  # Reemplazar B.le (salto condicional) con B (incondicional)
  %(prog)s libapp.so 01000054 00000014 --all

Patrones ARM64 comunes (hex little-endian):
  00000000          NOP
  00008052          MOV W0, #0x0
  20008052          MOV W0, #0x1
  C0035FD6          RET
  F30300AA          MOV X19, X3
  000050B4          CBZ X0, <offset>  (ejemplo, el offset varía)
"""
    )
    parser.add_argument("binary", help="Input binary file (.so, executable)")
    parser.add_argument("pattern", help="Hex pattern to search (little-endian, sin espacios)")
    parser.add_argument("replacement", help="Hex replacement (must be same length as pattern)")
    parser.add_argument("--all", action="store_true", help="Patch all occurrences (default: ask)")
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=-1,
                        help="Patch at specific file offset (hex ok: 0x3b24e0)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file (default: overwrite input)")
    parser.add_argument("--backup", action="store_true",
                        help="Create .bak backup before patching")

    args = parser.parse_args()

    # Validar archivo
    if not os.path.isfile(args.binary):
        print(f"[-] File not found: {args.binary}")
        sys.exit(1)

    # Parsear hex
    try:
        pattern_bytes = parse_hex_string(args.pattern)
        replacement_bytes = parse_hex_string(args.replacement)
    except ValueError as e:
        print(f"[-] Invalid hex string: {e}")
        sys.exit(1)

    if len(pattern_bytes) != len(replacement_bytes):
        print(f"[-] Pattern and replacement must have same length (pattern: {len(pattern_bytes)} bytes, replacement: {len(replacement_bytes)} bytes)")
        sys.exit(1)

    if len(pattern_bytes) == 0:
        print("[-] Pattern cannot be empty")
        sys.exit(1)

    # Backup
    if args.backup:
        backup_path = args.binary + ".bak"
        import shutil
        shutil.copy2(args.binary, backup_path)
        print(f"[+] Backup created: {backup_path}")

    # Parchear
    output_path = args.output if args.output else args.binary
    try:
        n = patch_binary(
            args.binary,
            output_path,
            pattern_bytes,
            replacement_bytes,
            offset=args.offset,
            replace_all=args.all
        )
        if n > 0:
            print(f"\n[+] Successfully applied {n} patch(es).")
            if args.offset >= 0:
                print_disassembly_hint(args.offset, output_path)
    except ValueError as e:
        print(f"[-] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
