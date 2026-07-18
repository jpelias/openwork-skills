#!/usr/bin/env python3
"""
Neutralize public static dialog entry methods injected by common modders (yhf/liteapks and variants)
without deleting classes (avoids NoClassDefFoundError).

Detection pattern:
  .method public static <name>(Landroid/content/Context;)(V|L...;)

Patch strategy:
  - For void return: replace body with return-void
  - For object return: return null (const/4 v0, 0x0; return-object v0)

Usage:
  python3 neutralize_yhf_dialogs.py --roots dex_out dex2_out --write

Notes:
  - Skips typical framework/vendor directories.
  - Creates a .orig backup before writing.
  - Returning null is conservative y evita NPE si el caller comprueba nulidad; si no, combine con eliminación
    de call-sites en Activities para máxima robustez.
"""

from __future__ import annotations
import argparse
import os
import re

FRAMEWORK_DIR_TOKENS = (
    '/android/', '/androidx/', '/com/google/', '/dalvik/', '/java/', '/kotlin/', '/kotlinx/', '/io/flutter/'
)


def should_skip_dir(path: str) -> bool:
    p = path.replace('\\', '/').lower() + ('/' if not path.endswith('/') else '')
    return any(tok in p for tok in FRAMEWORK_DIR_TOKENS)


METHOD_RE = re.compile(
    r"(^\s*\.method\s+public\s+static\s+\w+\(Landroid/content/Context;\)(V|L[\w\/$]+;))",
    re.MULTILINE,
)


def patch_content(content: str) -> tuple[str, int]:
    patches = 0
    out = []
    i = 0
    lines = content.splitlines()
    n = len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"\s*\.method\s+public\s+static\s+(\w+)\(Landroid/content/Context;\)(V|L[\w\/$]+;)", line)
        if not m:
            out.append(line)
            i += 1
            continue
        # Found a target method. Collect signature and advance until .end method
        sig_line = line
        ret_type = m.group(2)

        # Find .end method
        j = i + 1
        while j < n and '.end method' not in lines[j]:
            j += 1
        if j >= n:
            # malformed; keep as-is
            out.append(line)
            i += 1
            continue

        if ret_type == 'V':
            body = [sig_line, '    .registers 1', '    return-void', '.end method']
        else:
            body = [sig_line, '    .registers 2', '    const/4 v0, 0x0', '    return-object v0', '.end method']
        out.extend(body)
        patches += 1
        i = j + 1  # skip original body including .end method
    return ('\n'.join(out) + ('\n' if not content.endswith('\n') else '')), patches


def main():
    ap = argparse.ArgumentParser(description='Neutraliza métodos estáticos de diálogos de modders (Context)')
    ap.add_argument('--roots', nargs='+', required=True, help='Directorios base (dex_out, dex2_out, ...)')
    ap.add_argument('--write', action='store_true', help='Aplicar cambios (sin esto solo informa)')
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
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
                new_content, patches = patch_content(content)
                if patches:
                    total_patches += patches
                    print(f'[+] {p}: {patches} método(s) neutralizado(s)')
                    if args.write:
                        bak = p + '.orig'
                        if not os.path.exists(bak):
                            try:
                                with open(bak, 'w', encoding='utf-8') as bf:
                                    bf.write(content)
                            except Exception:
                                pass
                        with open(p, 'w', encoding='utf-8') as wf:
                            wf.write(new_content)

    print(f'Explorados: {total_files} archivos; Métodos neutralizados: {total_patches}')
    if not args.write and total_patches > 0:
        print('Nota: use --write para aplicar cambios.')


if __name__ == '__main__':
    main()
