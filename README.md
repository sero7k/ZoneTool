# x64 ZoneTool

x64-zt is a standalone fastfile unlinker and linker for x64 Call of Duty titles. x64-zt can link, unlink, and convert assets between games with accurate conversions for the source & target engines in mind.

> [!WARNING]
> `main` contains the legacy x64-zt code. x64-zt 2 is a heavy rework of that code here on `develop`, and is pending release. [Pre-build releases](https://github.com/auroramod/x64-zt/releases/tag/develop-latest) contain x64-zt 2, but it is not guaranteed to work good yet.

## Supported games

| Codename | Game |
|---|---|
| **IW3** | Call of Duty 4: Modern Warfare *(dumping)* |
| **IW4** | Modern Warfare 2 *(dumping)* |
| **IW5** | Modern Warfare 3 *(dumping)* |
| **IW6** | Ghosts |
| **S1** | Advanced Warfare |
| **H1** | Modern Warfare Remastered |
| **H2** | Modern Warfare 2 Campaign Remastered |
| **S2** | WWII |
| **IW7** | Infinite Warfare |
| **IW8** | Modern Warfare (2019) |
| **T9** | Black Ops Cold War *(experimental)* |
| **S4** | Vanguard |

## Asset conversion

Rows are the source game. Columns are the `--target` game.

| From ↓ / To → | IW6 | S1 | H1 | H2 | S2 | IW7 | IW8 | T9 | S4 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **IW3** | 🚧 | 🚧 | 🚧 | 🚧 | 🚧 | ✅ | ❔ | ❌ | ❌ |
| **IW4** | 🚧 | 🚧 | 🚧 | 🚧 | 🚧 | 🚧 | ❔ | ❌ | ❌ |
| **IW5** | 🚧 | 🚧 | 🚧 | 🚧 | 🚧 | ⚠️ | ❔ | ❌ | ❌ |
| **IW6** | ✅ | ❌ | ✅ | ❔ | ❔ | ❌ | ❌ | ❌ | ❌ |
| **S1**  | ❌ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| **H1**  | ❌ | ❌ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| **H2**  | ❌ | ❌ | ✅ | ✅ | ❔ | ❌ | ❌ | ❌ | ❌ |
| **S2**  | ❌ | ❌ | ⚠️ | ❔ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **IW7** | ❌ | ❌ | ⚠️ | ❌ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| **IW8** | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ❌ |
| **T9**  | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🧪 | 🧪 | ❌ |
| **S4**  | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ✅ |

| | Status | Meaning |
|:-:|---|---|
| ✅ | **Supported** | Works for the assets of this game pair |
| ⚠️ | **Partial** | Unfinished (some assets may work like weapons) |
| 🧪 | **Experimental** | Broken or incorrect outputs |
| ❔ | **Possible** | Can be achieved via alternative conversions (like `IW5 -> IW7 -> IW8`) |
| 🚧 | **Planned** | x86 games from Joelrau/zonetool for dumping only |
| ❌ | **Not supported** | No conversion |

The [x64-zt documentation](https://docs.auroramod.dev/x64-zt#game-conversion-support) has more information about conversion if you're interested.

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

The v1 ZoneTool of this fork (hooks the game exe, in-process T7 dumpers) is kept on the `v1` branch.

## Guides

- [x64-zt](https://docs.auroramod.dev/x64-zt)
- [Zonetool Extra](https://docs.auroramod.dev/zonetool-extra)
- [Map porting IW3/4/5 → H1](https://docs.auroramod.dev/map-porting-iw5)
- [Map porting S1 ↔ H1 ↔ H2](https://docs.auroramod.dev/map-porting-s1)
- [Weapon porting H1 → S2](https://docs.auroramod.dev/h1-to-s2-weapon)
- [Weapon porting IW7 → IW8](https://docs.auroramod.dev/iw7-to-iw8-weapon)

If you get stuck, feel free to ask the community in the [Aurora Discord server](http://auroramod.dev/discord).
