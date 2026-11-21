# x64 ZoneTool
A fastfile unlinker and linker for various x64 Call of Duty titles. 

- If you are interested in porting maps or assets from IW3/4/5, check <b>[Aurora's Map Porting IW3/4/5 -> H1](https://docs.auroramod.dev/map-porting-iw5)</b>
- If you are interested in porting maps or assets from newer Call of Duty games like H1, S1, H1, H2, or IW7, between each other, check <b>[Aurora's Map Porting (S1 <-> H1 <-> H2)](https://docs.auroramod.dev/map-porting-s1)</b>

## Supported Games
* **IW6** (*Call of Duty: Ghosts*)
* **S1** (*Call of Duty: Advanced Warfare*)
* **T7** (*Call of Duty: Black Ops 3*) ***[dumping only]***
* **H1** (*Call of Duty: Modern Warfare Remastered*)
* **H2** (*Call of Duty: Modern Warfare 2 Campaign Remastered*)
* **IW7** (*Call of Duty: Infinite Warfare*) ***[no custom maps]***

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

## Asset Conversion Support

The table below shows which asset conversions are currently supported.

- **Rows** = Source game
- **Columns** = Target game

Legend:
- ✔️ Fully supported
- ⚠️ Partially supported (experimental)
- ❌ Not supported

| **From ↓ / To →** | **IW6** | **S1** | **H1** | **H2** | **T7** | **IW7** |
|-------------------|:-------:|:------:|:------:|:------:|:------:|:-------:|
| **IW6** | ✔️ | ❌ | ✔️ | ✔️ | ❌ | ❌ |
| **S1**  | ❌ | ✔️ | ✔️ | ✔️ | ❌ | ❌ |
| **H1**  | ❌ | ⚠️ | ✔️ | ✔️ | ❌ | ⚠️ |
| **H2**  | ❌ | ❌ | ✔️ | ✔️ | ❌ | ❌ |
| **T7**  | ❌ | ❌ | ⚠️ | ❌ | ✔️ | ⚠️ |
| **IW7** | ❌ | ❌ | ❌ | ❌ | ❌ | ✔️ |
