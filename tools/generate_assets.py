#!/usr/bin/env python3
"""Generate PBR assets for the Vibrant Visuals Showcase pack.

Derives MERS (metalness / emissive / roughness / subsurface) maps and
heightmaps from the vanilla Bedrock base color textures, writes the matching
*.texture_set.json files plus textures_list.json, generates both pack icons,
and emits the GameTest platform .mcstructure.

Usage:
    python3 tools/generate_assets.py --vanilla-dir /path/to/bedrock-samples/resource_pack/textures/blocks
"""

import argparse
import json
import math
import os
import shutil
import struct

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP_BLOCKS = os.path.join(REPO, "packs", "VibrantVisualsRP", "textures", "blocks")
RP_TEXTURES = os.path.join(REPO, "packs", "VibrantVisualsRP", "textures")
RP_ROOT = os.path.join(REPO, "packs", "VibrantVisualsRP")
BP_ROOT = os.path.join(REPO, "packs", "VibrantVisualsBP")

# Per-block PBR recipes. Channels are 0-255:
#   metalness: uniform metal mask
#   roughness: base roughness, modulated +/- by per-pixel luminance variance
#   emissive:  "luma" scales emissive by pixel brightness, "threshold" only
#              emits on pixels brighter than the given luminance
#   subsurface: uniform translucency (foliage)
#   heightmap: derive a parallax heightmap from luminance
BLOCKS = {
    "stone":        {"metal": 0, "rough": 215, "height": True},
    "cobblestone":  {"metal": 0, "rough": 230, "height": True},
    "brick":        {"metal": 0, "rough": 210, "height": True},
    "stonebrick":   {"metal": 0, "rough": 205, "height": True},
    "planks_oak":   {"metal": 0, "rough": 190, "height": True},
    "sand":         {"metal": 0, "rough": 235, "height": True},
    "gravel":       {"metal": 0, "rough": 240, "height": True},
    "obsidian":     {"metal": 0, "rough": 45},
    "glass":        {"metal": 0, "rough": 18},
    "iron_block":   {"metal": 255, "rough": 60},
    "gold_block":   {"metal": 255, "rough": 40},
    "copper_block": {"metal": 255, "rough": 95},
    "diamond_block": {"metal": 40, "rough": 30},
    "emerald_block": {"metal": 40, "rough": 35},
    "glowstone":    {"metal": 0, "rough": 185, "emissive": ("luma", 1.0)},
    "sea_lantern":  {"metal": 0, "rough": 90, "emissive": ("threshold", 170)},
    "shroomlight":  {"metal": 0, "rough": 165, "emissive": ("luma", 0.9)},
    "magma":        {"metal": 0, "rough": 225, "emissive": ("threshold", 110)},
    "azalea_leaves": {"metal": 0, "rough": 200, "subsurface": 200},
}


def luminance(px):
    return 0.2126 * px[0] + 0.7152 * px[1] + 0.0722 * px[2]


def build_mers(base: Image.Image, recipe: dict) -> Image.Image:
    w, h = base.size
    out = Image.new("RGBA", (w, h))
    src = base.convert("RGBA").load()
    dst = out.load()
    lumas = [[luminance(src[x, y]) for x in range(w)] for y in range(h)]
    mean = sum(sum(row) for row in lumas) / (w * h)
    for y in range(h):
        for x in range(w):
            l = lumas[y][x]
            metal = recipe.get("metal", 0)
            # Darker crevices read rougher, bright facets smoother.
            rough = recipe.get("rough", 220) + int((mean - l) * 0.25)
            rough = max(0, min(255, rough))
            emissive = 0
            if "emissive" in recipe:
                mode, p = recipe["emissive"]
                if mode == "luma":
                    emissive = int(min(255, l * p))
                elif mode == "threshold":
                    emissive = int(min(255, l * 1.3)) if l >= p else 0
            sss = recipe.get("subsurface", 0)
            dst[x, y] = (metal, emissive, rough, sss)
    return out


def build_heightmap(base: Image.Image) -> Image.Image:
    w, h = base.size
    out = Image.new("L", (w, h))
    src = base.convert("RGBA").load()
    dst = out.load()
    vals = [[luminance(src[x, y]) for x in range(w)] for y in range(h)]
    lo = min(min(r) for r in vals)
    hi = max(max(r) for r in vals)
    span = max(hi - lo, 1.0)
    for y in range(h):
        for x in range(w):
            # Compress into the 96-176 band to keep parallax subtle.
            dst[x, y] = int(96 + (vals[y][x] - lo) / span * 80)
    return out


def generate_textures(vanilla_dir: str):
    os.makedirs(RP_BLOCKS, exist_ok=True)
    listed = []
    for name, recipe in BLOCKS.items():
        src_path = os.path.join(vanilla_dir, f"{name}.png")
        base = Image.open(src_path).convert("RGBA")
        base.save(os.path.join(RP_BLOCKS, f"{name}.png"))
        build_mers(base, recipe).save(os.path.join(RP_BLOCKS, f"{name}_mers.png"))
        tset = {
            "format_version": "1.21.30",
            "minecraft:texture_set": {
                "color": name,
                "metalness_emissive_roughness_subsurface": f"{name}_mers",
            },
        }
        listed += [f"textures/blocks/{name}", f"textures/blocks/{name}_mers"]
        if recipe.get("height"):
            build_heightmap(base).save(os.path.join(RP_BLOCKS, f"{name}_heightmap.png"))
            tset["minecraft:texture_set"]["heightmap"] = f"{name}_heightmap"
            listed.append(f"textures/blocks/{name}_heightmap")
        with open(os.path.join(RP_BLOCKS, f"{name}.texture_set.json"), "w") as f:
            json.dump(tset, f, indent=2)
            f.write("\n")
    with open(os.path.join(RP_TEXTURES, "textures_list.json"), "w") as f:
        json.dump(sorted(listed), f, indent=2)
        f.write("\n")
    print(f"textures: {len(BLOCKS)} blocks -> {len(listed)} files")


def generate_icons():
    # Resource pack: sunset sky over wavy water.
    im = Image.new("RGB", (256, 256))
    d = ImageDraw.Draw(im)
    for y in range(150):
        t = y / 150
        d.line([(0, y), (256, y)], fill=(int(20 + 60 * t), int(60 + 80 * t), int(140 + 80 * t)))
    d.ellipse([96, 70, 160, 134], fill=(255, 214, 120))
    for y in range(150, 256):
        t = (y - 150) / 106
        base = (int(10 + 20 * t), int(70 - 30 * t), int(120 - 40 * t))
        d.line([(0, y), (256, y)], fill=base)
    for y in range(155, 256, 8):
        for x in range(0, 256, 4):
            off = int(4 * math.sin(x / 18 + y))
            d.point((x + off, y), fill=(120, 200, 230))
    im.save(os.path.join(RP_ROOT, "pack_icon.png"))

    # Behavior pack: dark slate with point-light dots over a platform.
    im = Image.new("RGB", (256, 256), (24, 26, 38))
    d = ImageDraw.Draw(im)
    d.rectangle([32, 170, 224, 196], fill=(90, 90, 100))
    for i, c in enumerate([(255, 182, 110), (255, 42, 0), (77, 228, 255), (180, 77, 255), (124, 255, 77)]):
        x = 56 + i * 38
        d.line([(x, 140), (x, 170)], fill=(60, 60, 70), width=4)
        d.ellipse([x - 12, 122, x + 12, 146], fill=c)
        for r in (18, 26):
            d.ellipse([x - r, 134 - r, x + r, 134 + r], outline=tuple(v // 3 for v in c))
    im.save(os.path.join(BP_ROOT, "pack_icon.png"))
    print("icons: 2 generated")


# --- Minimal little-endian NBT writer for .mcstructure -----------------------

def _tag(buf, tag_id, name):
    buf += struct.pack("<bH", tag_id, len(name)) + name.encode()


def _int(buf, name, val):
    _tag(buf, 3, name)
    buf += struct.pack("<i", val)


def _int_list(buf, name, vals):
    _tag(buf, 9, name)
    buf += struct.pack("<bi", 3, len(vals))
    buf += struct.pack(f"<{len(vals)}i", *vals)


def generate_structure():
    """17x8x17 GameTest arena: smooth stone floor, air above."""
    sx, sy, sz = 17, 8, 17
    layer0 = []
    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                layer0.append(0 if y == 0 else 1)
    layer1 = [-1] * (sx * sy * sz)

    buf = bytearray()
    buf += struct.pack("<bH", 10, 0)  # root compound, empty name
    _int(buf, "format_version", 1)
    _int_list(buf, "size", [sx, sy, sz])

    _tag(buf, 10, "structure")
    _tag(buf, 9, "block_indices")
    buf += struct.pack("<bi", 9, 2)  # list of 2 lists
    for layer in (layer0, layer1):
        buf += struct.pack("<bi", 3, len(layer))
        buf += struct.pack(f"<{len(layer)}i", *layer)
    _tag(buf, 9, "entities")
    buf += struct.pack("<bi", 0, 0)  # empty list
    _tag(buf, 10, "palette")
    _tag(buf, 10, "default")
    _tag(buf, 9, "block_palette")
    buf += struct.pack("<bi", 10, 2)
    for block in ("minecraft:smooth_stone", "minecraft:air"):
        _tag(buf, 8, "name")
        buf += struct.pack("<H", len(block)) + block.encode()
        _tag(buf, 10, "states")
        buf += b"\x00"  # end of states
        _int(buf, "version", 18168865)
        buf += b"\x00"  # end of palette entry
    _tag(buf, 10, "block_position_data")
    buf += b"\x00"
    buf += b"\x00"  # end default
    buf += b"\x00"  # end palette
    buf += b"\x00"  # end structure

    _int_list(buf, "structure_world_origin", [0, 0, 0])
    buf += b"\x00"  # end root

    out = os.path.join(BP_ROOT, "structures", "vibrantvisuals", "showcase.mcstructure")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(buf)
    print(f"structure: {out} ({len(buf)} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla-dir", required=True,
                    help="Path to bedrock-samples/resource_pack/textures/blocks")
    args = ap.parse_args()
    generate_textures(args.vanilla_dir)
    generate_icons()
    generate_structure()
