#!/usr/bin/env python3
"""
Patch default boolean values in smali code when reading SharedPreferences.

Usage:
  python3 patch_shared_prefs_defaults.py --roots dex_out dex2_out --keys premium noads pro --write

Behavior:
  - Searches for patterns like:
        const-string vX, "premium"
        const/4    vY, 0x0
        invoke-interface {v0, vX, vY}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    and flips 0x0 -> 0x1 (false -> true) for the default value only.
  - Skips files under framework packages (android/, androidx/, com/google/, dalvik/, java/, kotlin/).
  - Creates a .bak once per modified file.

Note:
  - This only changes the default value used when a key is missing. If the app later overwrites the stored value
    from Billing/servidor, prefer a getter-hook strategy (ver SKILL.md Step 5d) o Morphe.
"""

from __future__ import annotations
import argparse
import os
import re
from typing import List


FRAMEWORK_DIR_TOKENS = (
    '/android/', '/androidx/', '/com/google/', '/dalvik/', '/java/', '/kotlin/', '/kotlinx/', '/io/flutter/'
)


def should_skip_dir(path: str) -> bool:
    p = path.replace('\\', '/').lower() + ('/' if not path.endswith('/') else '')
    return any(tok in p for tok in FRAMEWORK_DIR_TOKENS)


def patch_file(path: str, keys: List[str]) -> int:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.read().splitlines()

    modified = 0
    i = 0
    # Precompile for speed
    key_set = set(keys)
    const_string_re = re.compile(r'^\s*const-string\s+v\d+,\s+"([^"]+)"')
    getboolean_call_re = re.compile(r'getBoolean\(Ljava/lang/String;Z\)Z')

    while i < len(lines):
        m = const_string_re.match(lines[i])
        if not m:
            i += 1
            continue
        key = m.group(1)
        # Match simple suffix too (common en apps con prefijos de paquete)
        if not (key in key_set or any(key.endswith(k) for k in key_set)):
            i += 1
            continue

        # Look ahead a few lines until we hit an invoke to getBoolean or we leave block
        changed_here = False
        for j in range(1, 7):
            k = i + j
            if k >= len(lines):
                break
            line = lines[k]
            # Stop if another const-string appears (next key)
            if 'const-string' in line:
                break
            if getboolean_call_re.search(line):
                # Try to flip a preceding const/4 0x0 to 0x1 within a small window
                for t in range(1, 5):
                    p = k - t
                    if p <= i:
                        break
                    if 'const/4' in lines[p] and '0x0' in lines[p]:
                        lines[p] = lines[p].replace('0x0', '0x1')
                        modified += 1
                        changed_here = True
                        break
                break
        i += 1

    if modified:
        bak = path + '.bak'
        try:
            if not os.path.exists(bak):
                with open(bak, 'w', encoding='utf-8') as bf:
                    bf.write('\n'.join(lines))  # write later? keep original? We'll back up original below
        except Exception:
            pass
    return modified, lines


def main():
    ap = argparse.ArgumentParser(description='Patch default boolean values for SharedPreferences.getBoolean in smali')
    ap.add_argument('--roots', nargs='+', required=True, help='Directorios base (por ejemplo dex_out dex2_out ...)')
    ap.add_argument('--keys', nargs='+', required=True, help='Claves a forzar por defecto a true (p.ej. premium noads pro)')
    ap.add_argument('--write', action='store_true', help='Escribir cambios (por defecto solo informa)')
    args = ap.parse_args()

    total_files = 0
    total_patches = 0
    for root in args.roots:
        for dirpath, _, filenames in os.walk(root):
            if should_skip_dir(dirpath):
                continue
            for fn in filenames:
                if not fn.endswith('.smali'):
                    continue
                total_files += 1
                p = os.path.join(dirpath, fn)
                modified, new_lines = patch_file(p, args.keys)
                if modified:
                    total_patches += modified
                    print(f'[+] {p}: {modified} cambio(s)')
                    if args.write:
                        # Backup original
                        bak = p + '.orig'
                        if not os.path.exists(bak):
                            try:
                                with open(p, 'r', encoding='utf-8', errors='ignore') as rf, \
                                     open(bak, 'w', encoding='utf-8') as wf:
                                    wf.write(rf.read())
                            except Exception:
                                pass
                        with open(p, 'w', encoding='utf-8') as wf:
                            wf.write('\n'.join(new_lines) + '\n')

    print(f'Explorados: {total_files} archivos; Cambios totales: {total_patches}')
    if not args.write and total_patches > 0:
        print('Nota: ejecute de nuevo con --write para aplicar cambios.')


if __name__ == '__main__':
    main()
