#!/usr/bin/env python3
"""
Strip old signatures, zipalign, and sign an APK.

Usage:
  python3 strip_sign_and_sign.py --in hacked.apk --out hacked_signed.apk
  python3 strip_sign_and_sign.py --in hacked.apk --out hacked_signed.apk \
    --ks /path/to/keystore.jks --ks-pass changeit --alias mykey

Generates a debug keystore at ~/.android/debug.keystore if none is provided.
"""

from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def find_tool(name: str) -> str:
    """Find a tool in PATH or common locations."""
    path = shutil.which(name)
    if path:
        return path
    # Common Android SDK locations
    candidates = [
        os.path.expanduser(f"~/Android/Sdk/build-tools/*/"),
        os.path.expanduser(f"~/Android/Sdk/platform-tools/"),
        "/usr/bin/",
        "/usr/local/bin/",
    ]
    for pattern in candidates:
        import glob
        for base in glob.glob(pattern):
            full = os.path.join(base, name)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return name  # fallback, let subprocess error if not found


def ensure_debug_keystore(ks_path: str) -> None:
    """Create a debug keystore if it doesn't exist."""
    if os.path.exists(ks_path):
        return
    os.makedirs(os.path.dirname(ks_path), exist_ok=True)
    keytool = find_tool("keytool")
    cmd = [
        keytool,
        "-genkey", "-v",
        "-keystore", ks_path,
        "-storepass", "android",
        "-alias", "androiddebugkey",
        "-keypass", "android",
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", "CN=Android Debug,O=Android,C=US",
    ]
    print(f"[+] Creating debug keystore at {ks_path}")
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser(description="Strip signatures, zipalign, and sign APK")
    ap.add_argument("--in", dest="inp", required=True, help="Input APK (unaligned, unsigned)")
    ap.add_argument("--out", dest="out", required=True, help="Output APK (signed)")
    ap.add_argument("--ks", help="Keystore path (default: ~/.android/debug.keystore)")
    ap.add_argument("--ks-pass", default="android", help="Keystore password")
    ap.add_argument("--alias", default="androiddebugkey", help="Key alias")
    ap.add_argument("--key-pass", default=None, help="Key password (default: same as ks-pass)")
    args = ap.parse_args()

    ks = args.ks or os.path.expanduser("~/.android/debug.keystore")
    key_pass = args.key_pass or args.ks_pass

    if not args.ks:
        ensure_debug_keystore(ks)

    zipalign = find_tool("zipalign")
    apksigner = find_tool("apksigner")

    # Step 1: zipalign
    aligned = tempfile.mktemp(suffix=".apk")
    print(f"[+] zipalign: {args.inp} -> {aligned}")
    result = subprocess.run(
        [zipalign, "-p", "-f", "4", args.inp, aligned],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[!] zipalign error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Step 2: apksigner sign
    print(f"[+] apksigner: {aligned} -> {args.out}")
    result = subprocess.run(
        [
            apksigner, "sign",
            "--ks", ks,
            "--ks-pass", f"pass:{args.ks_pass}",
            "--ks-key-alias", args.alias,
            "--key-pass", f"pass:{key_pass}",
            "--v1-signing-enabled", "true",
            "--v2-signing-enabled", "true",
            "--v3-signing-enabled", "true",
            "--out", args.out,
            aligned,
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[!] apksigner error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Cleanup
    os.unlink(aligned)

    # Verify
    print(f"[+] Verifying: {args.out}")
    subprocess.run(
        [apksigner, "verify", "--verbose", args.out],
        capture_output=False
    )
    print(f"\n[✓] Signed APK: {args.out}")


if __name__ == "__main__":
    main()
