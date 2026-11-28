# x64 ZoneTool (sero7k fork)
A fastfile unlinker and linker for x64 Call of Duty titles, based on [Aurora's x64-zt](https://github.com/auroramod/x64-zt) (`develop`, x64-zt 2), plus our map work for the CoD Legacy client. It reads fastfiles straight from the game folder and never runs the game.

## What's new in this fork
On top of Aurora's x64-zt:

### Black Ops II -> MWR map import (`importmap`) — new
- Imports a whole BO2 map from the files CodLegacy's exporter writes: world, spawns and entities, materials and real BO2 textures, sky.
- **Collision:** BO2's own clip mesh, world brushes and prop boxes (`<stem>.col`), so players walk on decks, stairs and props.
- **Lighting:** the map's own lightmap coordinates, BO2 reflection probes, and directional model lighting from BO2's light grid; surfaces cast sun shadows.
- Working in game on **`mp_carrier`**.

### Infinite Warfare -> MWR map port — improved
- Full map port used for `mp_flip`: world, collision, entities, materials, models, reflection probes, glass and effects.
- Effects (particle systems as H1 effects, flares, glass shards), reflective glass, IW7 metalness and gloss, per-area model lighting, lightmap baking tools.

### Newer games through ACTS — new
- `acts` command runs [atian-cod-tools](https://github.com/ate47/atian-cod-tools): dump BO3, BO4, Cold War, MW2019, Vanguard, MWII, MWIII, BO6 and BO7; link BO3 / BO4 / Cold War zones; GSC and hash tools.

### From Aurora (merged in)
- x64-zt 2: standalone, reads fastfiles directly (`-game <name> -path <folder>`).
- New games: WWII (S2), Modern Warfare 2019 (IW8), Vanguard (S4), Cold War (T9, experimental).

## Converting to MWR (H1)
What each game can be converted to *Modern Warfare Remastered* with today, what we plan to add, and how hard it is.

| Game | Converts to MWR now | Planned | How hard |
|---|---|---|---|
| **Ghosts** (IW6) | Maps and assets | — | Done (Aurora) |
| **Advanced Warfare** (S1) | Maps and assets | — | Done (Aurora) |
| **MW2 Campaign Remastered** (H2) | Maps and assets | — | Done (Aurora) |
| **WWII** (S2) | Maps and assets, partly | — | Easy (Aurora is finishing it) |
| **Infinite Warfare** (IW7) | Maps (`mp_flip` ported) | Better lighting and glass | Medium |
| **Black Ops II** (T6) | Maps (`mp_carrier` working) | Every BO2 map, then menus and UI, then weapons | Maps medium (~3–8 h each now the pipeline exists); weapons and animations hard |
| **CoD4, MW2, MW3** (IW3/4/5) | Through [Aurora's IW3/4/5 tools](https://docs.auroramod.dev/map-porting-iw5) | Aurora plans dumping in x64-zt | Done (other tool) |
| **World at War** (T4) | Dome ported with our own scripts | Move the steps into ZoneTool | Medium |
| **Black Ops III** (T7) | Images and materials (`v1` branch only) | Maps later | Hard: no map converter yet, the map format needs to be worked out |
| **Modern Warfare 2019** (IW8) | No (only to IW7) | Not yet | Very hard: newer renderer and materials |
| **Vanguard** (S4) | No (only to MW2019) | Ideas only | Very hard: would go S4 -> IW8 -> IW7 -> H1, or a new converter |
| **Cold War** (T9) | No (experimental dumping, to MW2019) | Ideas only | Very hard: newer engine and materials |
| **BO4, MWII, MWIII, BO6, BO7** | No (can be dumped through ACTS) | Ideas only | Very hard: newer engines, streamed assets, different materials and lighting |

**How hard:** Easy = mostly done, needs tidying. Medium = works, needs per-map polish. Hard = big pieces still missing. Very hard = a new converter from scratch.

## Quick start

1. Put `zonetool.exe` in the game folder, next to the game exe. x64-zt selects the game automatically.
2. Dump a zone:

   ```bash
   zonetool.exe dumpzone mp_shipment
   ```

   The assets and `mp_shipment.csv` go to `dump/mp_shipment/`.
3. Put the asset files in `zonetool/<name>/` and the asset list (source CSV for your mod/map) in `zone_source/<name>.csv`. A dump CSV is a good start, or `generatecsv` command for maps. Then build:

   ```bash
   zonetool.exe buildzone <name>
   ```

   The result is `zone/<name>.ff` in the game folder.

> [!CAUTION]
> `buildzone` replaces a zone that has the same name. Back up the stock zone first, or give your zone a new name.

The [x64-zt documentation](https://docs.auroramod.dev/x64-zt) has every command and option, conversion with `--target`, the folder layout and the common errors.

## Building

You can use `generate.bat`, which uses Visual Studio 2022/2026 and Windows to do so. You can supply specific games through the generate file to include games you're not actively working on:

```bash
generate.bat --games=h1,iw7
```

| Option | Effect |
|---|---|
| `--games=<list>` | Games to build: `all` (default), or a list such as `h1,s2,iw7` |
| `--no-convert` | Skips the converter projects |
| `--copy-to=<folder>` | Copies `zonetool.exe` to this folder after each build |

Then open `build/x64-zt.sln`, or build Release x64 with MSBuild. The result is `build/bin/x64/Release/zonetool.exe`. A converter builds only when its source and target games are both selected.

## This fork

This fork is x64-zt (`develop`) plus the map work for the CoD Legacy client.

### Black Ops II map import (H1)

`importmap` reads the `.h1map` export of the CoD Legacy tool (`bo2_h1_export`) and writes the H1 map assets to `dump/<map>/`:
`maps/mp/<map>.d3dbsp.*` (gfx, clip, com, phys, fx, glass, ents), one material per Black Ops II material (`materials/wc/bo2_*.json`), the images it copies and `maps/mp/<map>.materials.csv` (the material lines for `zone_source/<map>.csv`).

```bash
zonetool.exe importmap bo2_import/carrier/mp_carrier.h1map -game h1 -path <MWR folder>
```

The importer also reads these files next to the `.h1map` when they exist:

| File | Use |
|---|---|
| `<stem>.mats.tsv` | material kinds and image names |
| `<stem>.h1lmuv` | the map's own lightmap coordinates |
| `<stem>.probes` | reflection probes (nearest probe per surface) |
| `<stem>.grid` / `<stem>.grid56` | light grid colour / 56 directional colours for models |
| `<stem>.col` | Black Ops II collision (mesh, world brushes, static model boxes) |
| `<map>.ents` | spawn and script entities |

Environment switches: `BO2_TRI_BUDGET` (collision triangle budget), `BO2_COL_RENDER` (collision from the drawn triangles, not `.col`), `BO2_COL_NO_COMPACT`, `BO2_COL_BOUNDS`.

### IW7 -> H1 maps

`dumpzone <map> --target h1 -game iw7` also converts the map: gfx world, clip map (with physics world, fx and glass world), com world, map ents, effects and particle systems (written when the zone ends) and createfx. `tools/iw7_lightbake.py`, `tools/iw7_lmdir.py` and `tools/iw7_lmtone.py` bake lightmaps from the exported lights.

### atian-cod-tools (ACTS)

`zonetool.exe acts ...` runs [ACTS](https://github.com/ate47/atian-cod-tools) (`acts.exe`) for games x64-zt does not read (BO3, BO4, Cold War, MW2019, Vanguard, MWII, MWIII, BO6, BO7): fastfile dumps, linkers, GSC tools and hash lookup. `zonetool.exe acts help` lists the commands and games.

ACTS is not linked into zonetool.exe. `deps/atian-cod-tools` is a submodule with `update = none`, so `generate.bat` skips it. `tools\build_acts.bat` builds it (CMake, vcpkg) into `build\bin\x64\Release\acts\`. A release `acts.exe` in `acts\` next to zonetool.exe, `-actspath <file>` or the `ZONETOOL_ACTS` variable also work. ACTS is GPL-3.0 or MIT, so keep its `LICENSE.md` and `licenses\` with the binaries.

ACTS dumps scripts and data tables, not images, models or worlds.

### v1

The old v1 ZoneTool of this fork (hooks the game exe, in-process Black Ops III dumpers, `ZT_DUMP_REFS`, old `-importmap` / `-buildzone` flags) is kept on the [`v1`](https://github.com/sero7k/ZoneTool/tree/v1) branch. Its builds are published as the [`v1-latest`](https://github.com/sero7k/ZoneTool/releases/tag/v1-latest) release, which the current Carrier build scripts use until they move to the new commands.

## Guides

- [x64-zt](https://docs.auroramod.dev/x64-zt)
- [Zonetool Extra](https://docs.auroramod.dev/zonetool-extra)
- [Map porting IW3/4/5 → H1](https://docs.auroramod.dev/map-porting-iw5)
- [Map porting S1 ↔ H1 ↔ H2](https://docs.auroramod.dev/map-porting-s1)
- [Weapon porting H1 → S2](https://docs.auroramod.dev/h1-to-s2-weapon)
- [Weapon porting IW7 → IW8](https://docs.auroramod.dev/iw7-to-iw8-weapon)

If you get stuck, feel free to ask the community in the [Aurora Discord server](http://auroramod.dev/discord).
