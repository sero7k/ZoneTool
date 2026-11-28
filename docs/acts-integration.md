# atian-cod-tools (ACTS) integration

This branch brings [ate47/atian-cod-tools](https://github.com/ate47/atian-cod-tools) (ACTS) into ZoneTool.
ACTS is vendored as a git submodule (`deps/atian-cod-tools`, pinned to `afb5713`, 2026-11-21) and
ZoneTool runs the ACTS CLI (`acts.exe`) through a small bridge (`src/zonetool/acts/acts_bridge.*`).

## Licence

| Project | Licence | Notes |
| --- | --- | --- |
| ZoneTool (this fork) | GPL-3.0 (`LICENSE`) | |
| ACTS | dual **GPL-3.0 or MIT**, your choice (`deps/atian-cod-tools/LICENSE.md`) | its `gpl` CMake preset also pulls in xensik/gsc-tool (GPL-3) for IW-engine scripts |

Both licences let ACTS code be copied into, or linked with, a GPL-3 project, so vendoring is fine.
Keep `LICENSE.md` and `licenses/` with any ACTS binaries you ship (`tools/build_acts.bat` copies them).
The new BO3 code in `src/zonetool/zonetool/t7` (offline fastfile reader, image/material dumpers) is
written from scratch from the format, so it does not depend on the ACTS licence.

## Why a process bridge rather than linking

ACTS builds with CMake, vcpkg and VS 2026 and uses about 25 submodules (Qt optional, CascLib, curl,
libtom, gsc-tool, ...). ZoneTool builds with premake and a different set of dependencies. Linking
`acts-common` into `zonetool.exe` would mean rebuilding ACTS's dependency graph in premake and fixing
clashes (two zlib/zstd/libtom copies, json versions). Running `acts.exe` as a child process:

- keeps both builds independent, so updating ACTS is a submodule bump;
- avoids symbol and CRT clashes inside ZoneTool's fixed-base game loader process;
- keeps the cost low: ACTS handlers are batch jobs that write files to disk.

The submodule has `update = none` in `.gitmodules`, so `generate.bat` (recursive submodule update)
does not clone ACTS and vcpkg for people who only build ZoneTool. `tools\build_acts.bat` fetches
and builds it on demand.

## Inventory

"Fork" is what this ZoneTool fork had before this branch. "Now" is what this branch adds.

### Fastfile dumping

| Game | ACTS handler | ACTS pools (from ACTS README) | Fork before | Now |
| --- | --- | --- | --- | --- |
| Black Ops 3 | `bo3` | rawfile, scriptparsetree | **in-process** via `BlackOps3_UnrankedDedicatedServer.exe` (all pools load; xmodel/xmodelmesh/xanim to H1 & IW7) | + image/material dump + H1 conversion, + offline `ffinfo`, + `-dumpzone bo3` through ACTS |
| Black Ops 4 | `bo4` | ~60 pools (scriptparsetree, stringtable, weapon, ddl, luafile, gfxworld/comworld (partial), ...) | none | `-dumpzone bo4` through ACTS |
| Black Ops Cold War | `cw` | rawfile, scriptparsetree, using, scriptbundle, bgcache, ddl, localizeentry, keyvaluepairs, weapon_frontend, zbarrier | none | `-dumpzone cw` through ACTS |
| Modern Warfare 2019 | `mw19` | rawfile, scriptfile (GPL build), luafile, localize | none (iw8 code may exist on a separate branch, see below) | `-dumpzone mw19` through ACTS |
| Vanguard | `vg` | rawfile, scriptfile (GPL build), luafile, localize | none | `-dumpzone vg` through ACTS |
| Modern Warfare II (+SP) | `mwii`, `mwiisp` | rawfile, scriptfile (GPL), luafile, stringtable, ddl, scriptbundle, localize | none | `-dumpzone mwii/mwiisp` through ACTS |
| Modern Warfare III (+SP) | `mwiii`, `mwiiisp` | rawfile, gscobj, luafile, stringtable, ddl, scriptbundle, localize | none | `-dumpzone mwiii/mwiiisp` through ACTS |
| Black Ops 6 (+SP) | `bo6`, `bo6sp` | rawfile, gscobj, gscgdb, luafile, aitype, scriptbundle, stringtable, kvp, operator*, ddl, localize, soundbank, ... | none | `-dumpzone bo6/bo6sp` through ACTS |
| Black Ops 7 | `bo7` | same family as BO6 | none | `-dumpzone bo7` through ACTS |

**Important:** ACTS dumps scripts and data tables. Apart from partial BO4 world data it does **not**
export images, materials, xmodels, clipmaps or gfxworlds, which are what porting to H1/HMW needs.
Geometry and texture conversion still has to be native ZoneTool code (the `t7` module for BO3) or
come from Greyhound/Cordycep exports. For Cold War (the user's other game) that means:
ACTS gives scripts, string tables, bundles and weapon frontend data, but not models or maps.

### Other ACTS features

| Feature | ACTS | Fork before | Now |
| --- | --- | --- | --- |
| Fastfile linker BO3 / BO4 / CW | `fastfilelinker -l Bo3/Bo4/CW` | none (`buildzone` exists only for IW titles) | `-linkzone <game> <dir>` |
| GSC decompiler (Treyarch T7/T8/T9/T10/SAT, IW JUP) | `gscinfo` | `deps/gsc-tool` (xensik) for IW-engine titles only | `-gscdecompile <files>` |
| GSC compiler | `gscc -g <vm>` | gsc-tool for IW titles | `-gsccompile <game> <files>` |
| Hash lookup / hash index | `lookup`, `h32`, `h64`, `ht7`, `download_hash_index`, `hashscan` | none | `-hashlookup <hashes>`, any other tool via `-acts <tool> ...` |
| BO3 `.fd` patch files (bdiff) | yes (`-p`) | no | via ACTS (`-- -p`); the native reader does not apply `.fd` patches yet |
| Encrypted fastfiles (AES-CTR, per-ff keys) | yes (bundled key DB) | no | via ACTS; the native reader rejects encrypted zones |
| Game exe dumping for module mapping | `game_dump <id> <path>` | n/a | `-acts game_dump bo3 <game dir>` |
| Cordycep/CSI pool export, PS4 tools, LUI tools, mods/DLLs | yes | no | not wrapped, use `-acts ...` or ACTS directly |

### IW-engine overlap (MW2019 / MWII / MWIII)

The coordinator mentioned iw8 code on a "v2" branch. This clone's remote only has `main` (plus
`acts-integration`), so the overlap could not be checked here. When that branch is available, compare
its iw8 asset readers with the ACTS `mw19` handler: ACTS only covers script/lua/localize pools for
MW2019, so native iw8 asset code (if any) would still be the only route for models and maps.

## Usage

Build ACTS once (needs VS 2026 + CMake; the first vcpkg configure is slow):

```bat
tools\build_acts.bat            REM output: build\bin\x64\Release\acts\
```

or download a release `acts.zip` from GitHub (check whether it is the GPL build; only the GPL build has the IW-engine script support)
and unpack it into `acts\` next to `zonetool.exe`. The bridge looks for `acts.exe` in:
`-actspath <path>`, `%ZONETOOL_ACTS%`, `<zonetool dir>\acts.exe`, `<zonetool dir>\acts\acts.exe`,
`<zonetool dir>\acts\bin\acts.exe` (then the same under the current directory).

ACTS handlers for BO3/BO4/CW/... map the game executable to reuse its load functions. Dump it once
per game with ACTS (`zonetool -acts game_dump <id> <game dir>`), or pass `-- -g <exe>`.

Commands (no game binary needed, `zonetool.exe` can be run from anywhere):

```bat
zonetool -dumpzone cw  <zone|path.ff> [asset types|_] [-gamepath <dir>] [-o <dir>] [-- extra acts args]
zonetool -dumpzone bo4 zm_towers
zonetool -dumpzone bo3 mp_sector -acts-force   REM use ACTS even if the BO3 server exe is present
zonetool -linkzone bo3 my_mod_dir
zonetool -gscdecompile dump\cw\scriptparsetree -o dump\gsc
zonetool -gsccompile t7 scripts\
zonetool -hashlookup 0x1234abcd 0xdeadbeef
zonetool -acts <any acts tool and args>
zonetool -actshelp
```

Output defaults to `dump\<handler>\` under the current directory. Asset types are ACTS pool names,
comma separated (`-a` in ACTS). Inside the BO3 in-process console, `acts <args>` runs ACTS too.

## Not done / next steps

1. Build `acts.exe` with `tools\build_acts.bat` on Windows and run the commands above against the
   BO3 and Cold War game files (the bridge is untested on Windows; see `docs/bo3-support.md`).
2. Optional: an in-process route for Cold War like the BO3 one (load the CW exe and hook
   `DB_AddXAsset`), which would give the geometry and image assets ACTS does not export. This is
   much larger work: CW uses the "flexible" fastfile format, Arxan, and a different asset set.
3. If the bridge proves too limiting, link `acts-common.dll` and call its exported C API
   (`ActsAPI*`, see `deps/atian-cod-tools/include/acts_api`) instead of spawning a process.
