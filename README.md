# Vibrant Visuals Showcase Add-On

A complete **Vibrant Visuals** (Deferred Technical Preview / Render Dragon) add-on for
Minecraft: Bedrock Edition, consisting of:

- **`packs/VibrantVisualsRP`** — resource pack implementing the full Advanced Rendering
  ("Deferred") JSON schema set: lighting, atmospherics, volumetric fog & light shafts,
  color grading & tone mapping, cubemap lighting, shadows, water, local (point/static)
  lights, PBR fallbacks, per-biome overrides, and **full-coverage PBR texture sets —
  generated normal (bump) maps and detail roughness maps for every vanilla block
  texture** (1,187 texture sets) so all surfaces render with depth.
- **`packs/VibrantVisualsBP`** — behavior pack with a **GameTest** that builds a lighting
  showcase platform (colored point lights, emissive blocks, a water pool, and metal
  reflection pedestals).
- **`dist/VibrantVisuals.mcaddon`** — the packaged add-on, ready to import.

Built against the schemas documented on the
[Minecraft Creator Portal](https://learn.microsoft.com/en-us/minecraft/creator/documents/vibrantvisuals/lightingcustomization?view=minecraft-bedrock-stable)
and structured after the official
[`microsoft/minecraft-samples` `deferred_lighting_starter`](https://github.com/microsoft/minecraft-samples/tree/main/deferred_lighting_starter)
project. Requires **Bedrock 1.21.120+** on a device that supports Vibrant Visuals.

---

## Installation

**Windows quick deploy (recommended for iteration):** double-click **`deploy.bat`**
(or `deploy.bat preview` for Minecraft Preview). It robocopies both packs into the
`com.mojang` `development_resource_packs` / `development_behavior_packs` folders, so
they appear under **My Packs** instantly — no import and no version bump needed.
Re-run it after any change and re-enter your world. `build_and_import.bat` instead
rebuilds the `.mcaddon` and opens it with Minecraft's importer.

**Or import the .mcaddon:**

1. Grab `dist/VibrantVisuals.mcaddon` and open it (double-click on Windows, share/open
   with Minecraft on mobile). Minecraft imports both packs.
2. Create a new world (Creative, Flat recommended) and:
   - apply **Vibrant Visuals Showcase** under *Resource Packs*,
   - apply **Vibrant Visuals Showcase GameTest** under *Behavior Packs*,
   - enable **Cheats** and the **Beta APIs** experiment (required by GameTest),
   - in *Settings → Video*, set **Graphics Mode** to **Vibrant Visuals**.

## Running the showcase

Two ways to spawn the test environment:

```
/gametest run vibrantvisuals:lighting_showcase
```

builds a 17×17 platform from `structures/vibrantvisuals/showcase.mcstructure`
(registered to the `night` batch so the lights pop), or — anywhere, no structure needed:

```
/scriptevent vibrant:showcase
```

builds the same platform next to the player. The platform contains:

| Row | Contents | What to inspect |
| --- | --- | --- |
| z=2 | torch, soul torch, redstone torch, lantern, soul lantern, end rod | true **point lights** with custom colors from `local_lighting/local_lighting.json` — specular highlights + dynamic shadows |
| z=5 | 8 lit colored candles | per-color point-light tinting |
| z=8 | glowstone, sea lantern, shroomlight, magma, crying obsidian | **static/emissive** lights + emissive MERS texture channels |
| z=11–14 | glass-walled water pool | **waves, caustics**, screen-space reflections, underwater volumetric fog |
| z=12–15 | gold/iron/diamond/emerald/copper pedestals | metalness/roughness from the PBR **texture sets** |

Useful while testing: `/time set noon`, `/time set sunset`, `/time set midnight` to sweep
the **keyframed** sun/ambient/atmospherics curves.

## Inspecting lighting with the Bedrock Debug Tools

The official [Debug Tools sample](https://learn.microsoft.com/en-us/minecraft/creator/casual/debugtools?view=minecraft-bedrock-stable)
(from [`microsoft/minecraft-samples/debug_tools`](https://github.com/microsoft/minecraft-samples/tree/main/debug_tools))
adds in-game "watch" probes that pair well with this pack:

1. Clone `minecraft-samples`, `cd debug_tools`, run `npm install` then `npm run local-deploy`
   (edit `.env-ingame` → `MINECRAFT_PRODUCT="BedrockGDK"` for retail instead of Preview).
2. Add the deployed `debug_tools` behavior + resource packs to your showcase world.
3. Give yourself the tools:
   `/give @s debug_tools:magnifying_glass` and `/give @s debug_tools:wrench`.
4. Use the magnifying glass to add watches. The **time-of-day watch** is the key one for
   Vibrant Visuals: the keyframe keys in `lighting/global.json` and
   `atmospherics/atmospherics.json` map time as `0.0 = noon`, `0.25 = sunset`,
   `0.5 = midnight`, `0.75 = sunrise` — watch the value live while the sky and sun
   illuminance interpolate between your keyframes.
5. Pair with the in-game profiler/content log to catch schema errors: malformed Vibrant
   Visuals JSON shows up in the **content log** (enable it in Settings → Creator).

## What's configured where

| Feature | File(s) | Notes |
| --- | --- | --- |
| Directional lights (sun/moon/End flash) | `lighting/global.json`, `lighting/nether.json`, `lighting/end.json` | Sun illuminance 1→100,000 lux and color keyframed across the day; identifiers `vibrant:default/nether/end_lighting` |
| Point & static lights | `local_lighting/local_lighting.json` | 1.21.120 schema; custom `light_color` + `light_type` for torches, lanterns, end rods, all 16 candles, and static colors for glowstone/sea lantern/shroomlight/magma/crying obsidian |
| Atmospherics | `atmospherics/*.json` | Rayleigh/Mie scattering, sun glare shape, horizon blend stops, zenith/horizon sky colors — all keyframed for the overworld |
| Volumetric fog & light shafts | `fogs/default_fog_settings.json`, `fogs/swamp_fog.json` | `volumetric` density + media coefficients (scattering/absorption) + Henyey-Greenstein g for air & water |
| Color grading & tone mapping | `color_grading/*.json` | shadows/midtones/highlights grading + color temperature; `generic` tone-map operator (same operator everywhere — operators don't blend) |
| Cubemaps | `cubemaps/cubemap.json` | keyframed ambient illuminance, sky/directional contribution, atmospheric & volumetric scattering toggles |
| Subsurface scattering | `textures/blocks/azalea_leaves_mers.png` (alpha channel), `pbr/global.json` | MERS **S** channel = 200 for leaves; actor fallback subsurface = 40 |
| Shadows | `shadows/shadows.json` | `blocky_shadows` style, 16-texel resolution |
| Water | `water/water.json`, `water/ocean.json`, `water/swamp.json` | particle concentrations (chlorophyll/sediment/CDOM), waves, caustics, `biome_water_color_contribution`; caustics + wave-enabled kept identical across files (they can't blend) |
| Per-biome customization | `biomes/*.client_biome.json` | 10 biomes wiring `minecraft:lighting_identifier`, `minecraft:atmosphere_identifier`, `minecraft:color_grading_identifier`, `minecraft:water_identifier`, `minecraft:fog_appearance` |
| Keyframe syntax | throughout `lighting/`, `atmospherics/`, `cubemaps/` | `{"time-of-day": value}` pairs, linear interpolation, 0.0 noon / 0.25 sunset / 0.5 midnight / 0.75 sunrise |
| PBR texture sets | `textures/blocks/*.texture_set.json` | **all 1,187 vanilla block texture sets** rebuilt: vanilla metalness/emissive/subsurface channels preserved, roughness maps gain per-pixel luminance detail, and every block gets a generated tangent-space **normal (bump) map** whose strength scales with its roughness — the docs' recommended depth path (heightmaps are the weaker alternative). The 4 fluid sets keep their hand-authored vanilla normal maps |

## Rebuilding

```bash
# regenerate textures/icons/structure from vanilla base textures
git clone --depth 1 --filter=blob:none --sparse https://github.com/Mojang/bedrock-samples.git /tmp/bedrock-samples
cd /tmp/bedrock-samples && git sparse-checkout set --skip-checks resource_pack/textures/blocks && cd -
pip install pillow
python3 tools/generate_assets.py --vanilla-dir /tmp/bedrock-samples/resource_pack/textures/blocks

# validate all JSON and package the .mcaddon
python3 build_mcaddon.py
```
