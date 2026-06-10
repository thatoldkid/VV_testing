#!/usr/bin/env python3
"""Generate PBR assets for the Vibrant Visuals Showcase pack.

Walks every *.texture_set.json in the vanilla Bedrock block textures and, for
each one:
  - copies the base color texture,
  - rebuilds the MERS map keeping Mojang's authored metalness / emissive /
    subsurface channels but adding per-pixel roughness variation derived from
    the color texture's luminance (dark crevices read rougher, bright facets
    smoother),
  - generates a tangent-space normal (bump) map from the color texture's
    luminance using a tiling Sobel filter, with bump strength scaled by the
    block's average roughness so polished surfaces stay near-flat while rough
    surfaces get pronounced depth (the four fluid sets that ship a vanilla
    normal map keep theirs),
  - writes the overriding *.texture_set.json.

Normal maps are used instead of heightmaps: the Vibrant Visuals docs note
heightmaps are the less capable path ("not as efficient and cannot represent
as many textures"), and in practice their converted bump contribution is far
weaker than a real normal map.

Also regenerates textures_list.json, both pack icons, and the GameTest
platform .mcstructure.

Usage:
    python3 tools/generate_assets.py --vanilla-dir /path/to/bedrock-samples/resource_pack/textures/blocks
"""

import argparse
import glob
import json
import math
import os
import struct

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP_BLOCKS = os.path.join(REPO, "packs", "VibrantVisualsRP", "textures", "blocks")
RP_TEXTURES = os.path.join(REPO, "packs", "VibrantVisualsRP", "textures")
RP_ROOT = os.path.join(REPO, "packs", "VibrantVisualsRP")
BP_ROOT = os.path.join(REPO, "packs", "VibrantVisualsBP")

# How strongly luminance variance perturbs the vanilla roughness channel.
ROUGHNESS_DETAIL = 0.30
# Bump strength range: flat-ish for mirror-smooth surfaces up to strong relief
# for fully rough ones (scaled by each block's average vanilla roughness).
NORMAL_STRENGTH_MIN = 1.0
NORMAL_STRENGTH_MAX = 5.0
MERS_KEYS = ("metalness_emissive_roughness_subsurface", "metalness_emissive_roughness")


def luminance(px):
    return 0.2126 * px[0] + 0.7152 * px[1] + 0.0722 * px[2]


def find_texture(vanilla_dir, ref):
    for ext in (".png", ".tga"):
        path = os.path.join(vanilla_dir, ref + ext)
        if os.path.isfile(path):
            return path
    return None


def load_mers(path):
    """Load a MERS image as RGBA; missing alpha means zero subsurface."""
    im = Image.open(path)
    if "A" in im.getbands():
        return im.convert("RGBA")
    rgb = im.convert("RGB")
    out = Image.new("RGBA", rgb.size)
    out.paste(rgb)
    # Default subsurface to 0, not the 255 that convert("RGBA") would give.
    out.putalpha(Image.new("L", rgb.size, 0))
    return out


def build_detail_mers(color_img, mers_img):
    """Vanilla M/E/S channels + luminance-modulated roughness detail."""
    if mers_img.size != color_img.size:
        mers_img = mers_img.resize(color_img.size, Image.NEAREST)
    w, h = color_img.size
    src_c = color_img.load()
    src_m = mers_img.load()
    out = Image.new("RGBA", (w, h))
    dst = out.load()
    lumas = [[luminance(src_c[x, y]) for x in range(w)] for y in range(h)]
    mean = sum(sum(row) for row in lumas) / (w * h)
    rough_total = 0
    for y in range(h):
        for x in range(w):
            m, e, r, s = src_m[x, y]
            # Scale detail down on already-smooth surfaces so polished metal
            # and glass stay near-mirror instead of going matte.
            delta = (mean - lumas[y][x]) * ROUGHNESS_DETAIL * (0.3 + 0.7 * r / 255.0)
            r2 = max(0, min(255, int(r + delta)))
            rough_total += r
            dst[x, y] = (m, e, r2, s)
    return out, rough_total / (w * h)


def build_normal_map(color_img, avg_roughness):
    """Tangent-space normal map from luminance via a tiling Sobel filter.

    Brighter pixels are treated as raised. Strength scales with the block's
    average roughness so glass/polished metal stay near-flat while stone,
    bark, and bricks get strong relief. Edges wrap, since block textures tile.
    """
    w, h = color_img.size
    src = color_img.load()
    vals = [[luminance(src[x, y]) for x in range(w)] for y in range(h)]
    lo = min(min(r) for r in vals)
    hi = max(max(r) for r in vals)
    span = max(hi - lo, 1.0)
    height = [[(vals[y][x] - lo) / span for x in range(w)] for y in range(h)]
    strength = NORMAL_STRENGTH_MIN + (NORMAL_STRENGTH_MAX - NORMAL_STRENGTH_MIN) * (
        avg_roughness / 255.0)

    out = Image.new("RGB", (w, h))
    dst = out.load()
    for y in range(h):
        ym, yp = (y - 1) % h, (y + 1) % h
        for x in range(w):
            xm, xp = (x - 1) % w, (x + 1) % w
            gx = (height[ym][xp] + 2 * height[y][xp] + height[yp][xp]) - (
                height[ym][xm] + 2 * height[y][xm] + height[yp][xm])
            gy = (height[yp][xm] + 2 * height[yp][x] + height[yp][xp]) - (
                height[ym][xm] + 2 * height[ym][x] + height[ym][xp])
            nx, ny, nz = -gx * strength, -gy * strength, 1.0
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
            dst[x, y] = (
                int((nx * inv * 0.5 + 0.5) * 255),
                int((ny * inv * 0.5 + 0.5) * 255),
                int((nz * inv * 0.5 + 0.5) * 255),
            )
    return out


def generate_textures(vanilla_dir):
    os.makedirs(RP_BLOCKS, exist_ok=True)
    listed = set()
    done = skipped = normals = 0
    for set_path in sorted(glob.glob(os.path.join(vanilla_dir, "*.texture_set.json"))):
        base = os.path.basename(set_path)[: -len(".texture_set.json")]
        with open(set_path, encoding="utf-8-sig") as f:
            ts = json.load(f)["minecraft:texture_set"]
        color_ref = ts.get("color")
        mers_key = next((k for k in MERS_KEYS if k in ts), None)
        mers_ref = ts.get(mers_key) if mers_key else None
        if not isinstance(color_ref, str) or not isinstance(mers_ref, str):
            skipped += 1
            continue
        color_path = find_texture(vanilla_dir, color_ref)
        mers_path = find_texture(vanilla_dir, mers_ref)
        if not color_path or not mers_path:
            skipped += 1
            continue

        color_img = Image.open(color_path).convert("RGBA")
        color_img.save(os.path.join(RP_BLOCKS, f"{color_ref}.png"))
        listed.add(f"textures/blocks/{color_ref}")

        mers_out, avg_rough = build_detail_mers(color_img, load_mers(mers_path))
        mers_out.save(os.path.join(RP_BLOCKS, f"{mers_ref}.png"))
        listed.add(f"textures/blocks/{mers_ref}")

        out_set = {
            "format_version": "1.21.30",
            "minecraft:texture_set": {
                "color": color_ref,
                "metalness_emissive_roughness_subsurface": mers_ref,
            },
        }
        if "normal" in ts:
            # Fluids ship a hand-authored vanilla normal map; keep it.
            out_set["minecraft:texture_set"]["normal"] = ts["normal"]
            normals += 1
        else:
            nm_name = f"{base}_normal_gen"
            build_normal_map(color_img, avg_rough).save(
                os.path.join(RP_BLOCKS, f"{nm_name}.png"))
            out_set["minecraft:texture_set"]["normal"] = nm_name
            listed.add(f"textures/blocks/{nm_name}")
        with open(os.path.join(RP_BLOCKS, f"{base}.texture_set.json"), "w") as f:
            json.dump(out_set, f, indent=2)
            f.write("\n")
        done += 1

    with open(os.path.join(RP_TEXTURES, "textures_list.json"), "w") as f:
        json.dump(sorted(listed), f, indent=2)
        f.write("\n")
    print(f"texture sets: {done} written ({normals} kept vanilla normal maps), "
          f"{skipped} skipped, {len(listed)} textures listed")


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
