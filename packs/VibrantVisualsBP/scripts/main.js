import * as GameTest from "@minecraft/server-gametest";
import { system, world, BlockPermutation } from "@minecraft/server";

// ---------------------------------------------------------------------------
// Vibrant Visuals lighting showcase
//
// Layout on a 17x17 smooth stone platform (coordinates relative to the
// structure origin, y=1 is the first layer above the floor):
//
//   z=2   point lights:   torch, soul torch, redstone torch, lantern,
//                         soul lantern, end rod
//   z=5   colored candles (point lights with per-color light_color from
//                         local_lighting/local_lighting.json)
//   z=8   emissive/static lights: glowstone, sea lantern, shroomlight, magma,
//                         crying obsidian
//   z=11..15  glass-walled water pool (waves + caustics + volumetric water fog)
//   z=15  reflection pedestals: gold, iron, diamond, emerald, copper blocks
// ---------------------------------------------------------------------------

const POINT_LIGHT_ROW = [
  "minecraft:torch",
  "minecraft:soul_torch",
  "minecraft:redstone_torch",
  "minecraft:lantern",
  "minecraft:soul_lantern",
  "minecraft:end_rod",
];

const CANDLE_ROW = [
  "minecraft:red_candle",
  "minecraft:orange_candle",
  "minecraft:yellow_candle",
  "minecraft:lime_candle",
  "minecraft:cyan_candle",
  "minecraft:blue_candle",
  "minecraft:purple_candle",
  "minecraft:magenta_candle",
];

const EMISSIVE_ROW = [
  "minecraft:glowstone",
  "minecraft:sea_lantern",
  "minecraft:shroomlight",
  "minecraft:magma",
  "minecraft:crying_obsidian",
];

const METAL_ROW = [
  "minecraft:gold_block",
  "minecraft:iron_block",
  "minecraft:diamond_block",
  "minecraft:emerald_block",
  "minecraft:copper_block",
];

/**
 * Builds the showcase. `setBlock(blockId, x, y, z)` and
 * `setPermutation(permutation, x, y, z)` abstract over GameTest-relative
 * placement vs. absolute world placement.
 */
function buildShowcase(setBlock, setPermutation) {
  // Row of classic point lights on pedestals.
  POINT_LIGHT_ROW.forEach((block, i) => {
    const x = 3 + i * 2;
    setBlock("minecraft:polished_blackstone", x, 1, 2);
    setBlock(block, x, 2, 2);
  });

  // Lit colored candles (3 candles per cluster for brightness).
  CANDLE_ROW.forEach((candle, i) => {
    const x = 1 + i * 2;
    const perm = BlockPermutation.resolve(candle, { lit: true, candles: 3 });
    setPermutation(perm, x, 1, 5);
  });

  // Emissive (static light) blocks.
  EMISSIVE_ROW.forEach((block, i) => {
    setBlock(block, 3 + i * 2, 1, 8);
  });

  // Water pool with glass walls: 7x4 outer rim, water inside.
  for (let x = 2; x <= 8; x++) {
    for (let z = 11; z <= 14; z++) {
      const isRim = x === 2 || x === 8 || z === 11 || z === 14;
      setBlock(isRim ? "minecraft:glass" : "minecraft:water", x, 1, z);
    }
  }
  // A lantern beside the pool so caustics and water reflections get a light.
  setBlock("minecraft:sea_lantern", 9, 1, 12);

  // Metal/gem pedestals for specular reflection inspection.
  METAL_ROW.forEach((block, i) => {
    setBlock(block, 11 + (i % 3) * 2, 1, 12 + Math.floor(i / 3) * 2);
  });
}

// --- GameTest entry ---------------------------------------------------------
// Run with: /gametest run vibrantvisuals:lighting_showcase
function lightingShowcase(test) {
  buildShowcase(
    (block, x, y, z) => test.setBlockType(block, { x, y, z }),
    (perm, x, y, z) => test.setBlockPermutation(perm, { x, y, z })
  );

  // Keep the scene alive long enough to fly around and inspect it, then pass.
  test.succeedOnTick(580);
}

GameTest.register("vibrantvisuals", "lighting_showcase", lightingShowcase)
  .structureName("vibrantvisuals:showcase")
  .maxTicks(600)
  .batch("night"); // run at night so point lights and emissives stand out

// --- Script event fallback ---------------------------------------------------
// Works without launching a GameTest (still needs Beta APIs experiment):
//   /scriptevent vibrant:showcase
// Builds the showcase 5 blocks in front of north-west of the player.
system.afterEvents.scriptEventReceive.subscribe((event) => {
  if (event.id !== "vibrant:showcase") return;
  const player = event.sourceEntity ?? world.getAllPlayers()[0];
  if (!player) return;

  const dim = player.dimension;
  const origin = {
    x: Math.floor(player.location.x) + 2,
    y: Math.floor(player.location.y) - 1,
    z: Math.floor(player.location.z) + 2,
  };

  // Floor first, then the showcase on top of it.
  for (let x = 0; x < 17; x++) {
    for (let z = 0; z < 17; z++) {
      trySetBlock(dim, "minecraft:smooth_stone", origin.x + x, origin.y, origin.z + z);
    }
  }
  buildShowcase(
    (block, x, y, z) => trySetBlock(dim, block, origin.x + x, origin.y + y, origin.z + z),
    (perm, x, y, z) => {
      const b = dim.getBlock({ x: origin.x + x, y: origin.y + y, z: origin.z + z });
      if (b) b.setPermutation(perm);
    }
  );
  player.sendMessage("§bVibrant Visuals showcase built! Toggle Vibrant Visuals in Video settings to compare.");
});

function trySetBlock(dim, block, x, y, z) {
  const target = dim.getBlock({ x, y, z });
  if (target) target.setType(block);
}
