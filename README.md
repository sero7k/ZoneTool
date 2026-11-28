# x64 ZoneTool
A fastfile unlinker and linker for various x64 Call of Duty titles. 

- If you are interested in porting maps or assets from IW3/4/5, check <b>[Aurora's Map Porting IW3/4/5 -> H1](https://docs.auroramod.dev/map-porting-iw5)</b>
- If you are interested in porting maps or assets from newer Call of Duty games like H1, S1, H1, H2, or IW7, between each other, check <b>[Aurora's Map Porting (S1 <-> H1 <-> H2)](https://docs.auroramod.dev/map-porting-s1)</b>

## What's new in this fork
Everything below is added on top of upstream [auroramod/x64-zt](https://github.com/auroramod/x64-zt).

### Black Ops II -> H1 map import (`importmap`) — new
- Imports a whole BO2 map from the files CodLegacy's exporter writes: world, spawns and entities, materials and real BO2 textures, sky.
- **Collision:** uses BO2's own clip mesh, world brushes and prop boxes (`<stem>.col`), so players walk on the deck, stairs and props instead of the render mesh.
- **Lighting:** the map's own lightmap coordinates (`.h1lmuv`), BO2 reflection probes (`.probes`), and a directional light grid for models taken from BO2's light grid (`.grid56`).
- Surfaces now cast sun shadows and use stock-style surface data, ocean surfaces set up like `mp_bog_summer`.
- Also runs from the command line: `zonetool -importmap <file.h1map>`.
- Working in game on **`mp_carrier`**.

### Infinite Warfare -> H1 map port — improved
- Full map port used for `mp_flip`: world, collision, entities, materials, models, reflection probes, glass and effects.
- Effects (particle systems approximated as H1 effects, flares as sprites, glass shards), reflective tower glass, IW7 metalness and gloss.
- Per-area model lighting through a real H1 light grid tree built from the baked lightmap; sun and emissives on IW7's tone curve.
- Adaptive collision detail; tools to bake spot lights and lightmaps.

### Black Ops III and newer games — new
- Black Ops III image and material dumping, with H1 conversion.
- ACTS bridge ([atian-cod-tools](https://github.com/ate47/atian-cod-tools)): dump BO4, Cold War, MW2019, Vanguard, MWII, MWIII, BO6 and BO7; link BO3 / BO4 / Cold War zones; GSC and hash tools.

### Other
- `ZT_DUMP_REFS` env var: H1 dumps also pull in the referenced assets (for example a map's ocean material and techset).
- CI builds every commit on `main` and publishes it as the [`latest`](https://github.com/sero7k/ZoneTool/releases/tag/latest) release.

## Converting to MWR (H1)
What each game can be converted to *Modern Warfare Remastered* with today, what we plan to add, and how hard it is.

| Game | Converts to MWR now | Planned | How hard |
|---|---|---|---|
| **Ghosts** (IW6) | Maps and assets | — | Done (upstream) |
| **Advanced Warfare** (S1) | Maps and assets | — | Done (upstream) |
| **MW2 Campaign Remastered** (H2) | Maps and assets | — | Done (upstream) |
| **WWII** (S2) | Maps and assets, partly (`v2` only) | Bring to the merged version | Easy |
| **Infinite Warfare** (IW7) | Maps (`mp_flip` ported) | Better lighting and glass | Medium |
| **Black Ops II** (T6) | Maps (`mp_carrier` working) | Every BO2 map, then menus and UI, then weapons | Maps medium (~3–8 h each now the pipeline exists); weapons and animations hard |
| **Black Ops III** (T7) | Images and materials only | Maps later | Hard: no map converter yet, the map format needs to be worked out |
| **World at War** (T4) | Dome ported with our own scripts | Move the steps into ZoneTool | Medium |
| **Modern Warfare 2019** (IW8) | No (only to IW7, `v2`) | Not yet | Very hard: newer renderer and materials |
| **BO4, Cold War, Vanguard, MWII, MWIII, BO6, BO7** | No (can be dumped through ACTS) | Ideas only | Very hard: newer engines, streamed assets, different materials and lighting |

- **How hard:** Easy = mostly done, needs tidying. Medium = works, needs per-map polish. Hard = big pieces still missing. Very hard = a new converter from scratch.
- CoD4, MW2 and MW3 (IW3/4/5) maps are ported with [Aurora's IW3/4/5 tools](https://docs.auroramod.dev/map-porting-iw5), not this repo.
- `main` and `v2` are being merged into one version. Until then, WWII and MW2019 are only on [`v2`](https://github.com/sero7k/ZoneTool/tree/v2); everything else is on `main`.
- BO2 import details: [docs/BO2_IMPORT.md](docs/BO2_IMPORT.md).

## How to use
Check out the [Aurora Zonetool Basics](https://docs.auroramod.dev/zonetool-basics) for useful guides & information on how to port maps and use zonetool.

## Commands
* `loadzone <zone>`: Loads a zone
* `unloadzones`: Unloads zones
* `verifyzone <zone>`: Lists assets in a zone
* `dumpzone <zone>`: Dumps a zone
* `dumpzone <target game> <zone> <asset filter>`: Dumps a zone converting assets for a specific game
* `dumpasset <type> <name>`: Dumps a single assset
* `dumpmap <map>`: Dumps all required assets for a map
* `dumpmap <target game> <map> <asset filter> <skip common>`: Dumps and converts all required assets for a map
* `importmap <file.h1map> [name]`: Imports a Black Ops II map (exported by CodLegacy's `bo2_h1_export`) as H1 map assets (H1 module)

  ### Definitions
  * `asset filter`: A filter specifying all the asset types that should be dumped, if not specified or empty it will dump all asset types.
  Asset types are separated by **commas**, **`_`** indicates and empty filter.   
    * Example: `dumpzone h1 mp_clowntown3 sound,material,techset,rawfile`
    * Example: `dumpmap h1 mp_clowntown3 _ true`
  * `skip common`: Skips common zones when dumping a map, can be `true` or `false`.
  * `target game`: The game to convert the assets to.

## ACTS bridge (BO4, Cold War, MW2019, Vanguard, MWII, MWIII, BO6, BO7)
ZoneTool can run [atian-cod-tools](https://github.com/ate47/atian-cod-tools) (vendored in `deps/atian-cod-tools`) for games without an in-process module, plus the ACTS linkers, GSC and hash tools:
* `zonetool -dumpzone <game> <zone>`: `bo3`, `bo4`, `cw`, `mw19`, `vg`, `mwii`, `mwiisp`, `mwiii`, `mwiiisp`, `bo6`, `bo6sp`, `bo7`
* `zonetool -linkzone <bo3|bo4|cw> <dir>`, `-gscdecompile`, `-gsccompile`, `-hashlookup`, `-acts <raw args>`

See [docs/acts-integration.md](docs/acts-integration.md) and [docs/bo3-support.md](docs/bo3-support.md).
