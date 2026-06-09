#!/usr/bin/env python3
"""Package the Vibrant Visuals resource + behavior packs into a .mcaddon.

A .mcaddon is a zip archive containing one folder per pack, each with a
manifest.json at its root. Run from the repository root:

    python3 build_mcaddon.py

Output: dist/VibrantVisuals.mcaddon
"""

import json
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
PACKS = os.path.join(REPO, "packs")
OUT = os.path.join(REPO, "dist", "VibrantVisuals.mcaddon")


def validate_pack(pack_dir: str) -> None:
    manifest = os.path.join(pack_dir, "manifest.json")
    if not os.path.isfile(manifest):
        sys.exit(f"ERROR: missing manifest.json in {pack_dir}")
    for root, _dirs, files in os.walk(pack_dir):
        for name in files:
            if name.endswith(".json"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8-sig") as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError as e:
                        sys.exit(f"ERROR: invalid JSON in {path}: {e}")


def main() -> None:
    pack_dirs = sorted(
        os.path.join(PACKS, d) for d in os.listdir(PACKS)
        if os.path.isdir(os.path.join(PACKS, d))
    )
    if not pack_dirs:
        sys.exit("ERROR: no packs found under packs/")

    for pack in pack_dirs:
        validate_pack(pack)
        print(f"validated {os.path.basename(pack)}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for pack in pack_dirs:
            base = os.path.basename(pack)
            for root, _dirs, files in os.walk(pack):
                for name in files:
                    full = os.path.join(root, name)
                    arc = os.path.join(base, os.path.relpath(full, pack))
                    zf.write(full, arc)
                    count += 1
    size_kb = os.path.getsize(OUT) / 1024
    print(f"wrote {OUT} ({count} files, {size_kb:.1f} KiB)")


if __name__ == "__main__":
    main()
