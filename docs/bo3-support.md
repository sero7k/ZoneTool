# Black Ops 3 (T7) support

## Starting point

This fork **already had** a `t7` module (`src/zonetool/zonetool/t7`, `src/zonetool/game/t7`,
`src/zonetool/component/t7`). Like the other ZoneTool modules it runs inside the game:
`zonetool.exe` sits next to `BlackOps3_UnrankedDedicatedServer.exe` (the free BO3 "Unranked Server"
tool on Steam), loads it, and hooks `DB_AddXAsset` / `DB_FinishLoadXFile`. The game's own loader
decompresses zones and follows pointers, so every asset type loads correctly. Before this branch:

- `t7` structs for all asset types (`t7/structs.hpp`, 3.4k lines), including GfxImage, Material,
  XModel, XModelMesh, XAnimParts, clipMap, GfxWorld, ComWorld and weapons;
- `.xpak` reader for streamed data (`t7/common/xpak.cpp`, LZ4 command blocks);
- converters `t7 -> h1` and `t7 -> iw7` for xmodel, xmodelmesh (from xpak) and xanim;
- `dumpzone t7 <zone>` was an empty dump (no native dumpers) and `loadzone`/`verifyzone`/`dumpcsv` listed assets.

So this branch builds on that module instead of adding a second, parallel BO3 module.

## Format notes (BO3 PC `.ff`, version 0x251)

These notes are written from the format (checked against ACTS `decompressor_t78.cpp` and
`handler_game_bo3.cpp`, which are dual GPL-3/MIT); the new code is a clean rewrite.

- Header `XFileHeader`, 0x248 bytes: `"TAff0000"`, u32 version (0x251 retail, 0x1FB beta,
  0x132 alpha uses a different layout), u8 server, u8 compression, u8 platform (0 pc), u8 encrypted,
  u64 timestamp, u32 changelist, u32 archiveChecksum[4], char builder[32], u32 metaVersion,
  char mergeFastfile[64], u64 size (decompressed), u64 externalSize, u64 memMappedOffset,
  u64 blockSize[10], char fastfileName[64], u8 signature[256] (RSA), u8 aesIV[16].
- Compression: 0 none, 1 zlib, 2 zlib HC, 3 LZ4, 4 LZ4 HC, 5/6 bdelta (patch files).
- Body: repeated `DBStreamHeader { u32 compressedSize, uncompressedSize, alignedSize, offset }` and
  `alignedSize` bytes. `offset` equals the file offset of that header. A header with
  `uncompressedSize == 0` is padding to the next 0x800000 boundary.
- Encrypted zones (`encrypted != 0`) are AES-CTR with a key per fastfile name and the header IV;
  the IV's low u64 advances by `compressedSize` per block. Not supported natively (ACTS has keys).
- `.fd` files are bdiff patches applied over the decompressed zone (not supported natively).
- XFile blocks (10): temp, runtime_virtual, runtime_physical, delay_virtual, delay_physical,
  virtual, physical, streamer_reserve, streamer, memmapped.
- The decompressed stream starts with `XAssetList` (0x30): `int stringsCount; char** strings;
  u32 unk10; void* unk18; int assetCount; XAsset* assets;` followed (pointer value -1) by the
  script-string pointer array, the inline strings, then `assetCount` × `{ int type; void* header; }`.
  Asset bodies follow and need per-type load code (the game's `Load_*` functions), which is why
  full offline loading is not attempted: ACTS also calls the mapped game exe for it.
- Streamed data (images, model meshes, sounds) lives in `zone/*.xpak` (`"KAPI"` magic), keyed by
  the 64-bit `XPakEntryInfo::key` stored in the asset.
- Asset type enum: `t7/structs.hpp` (`XAssetType`, 0x67 types; image 0x9, material 0x6,
  xmodel 0x4, xmodelmesh 0x5, clipmap 0xC, comworld 0xD, gfxworld 0x10, weapon 0x17).

## What this branch adds

| Area | File(s) | Status |
| --- | --- | --- |
| Offline `.ff` reader: header, block decompression (zlib/LZ4), XAssetList strings and asset-type table | `t7/common/fastfile.*` | written, untested on real zones |
| `ffinfo <zone> [true]` console command, `-ffinfo <zone>` command line: prints header, block sizes and per-type asset counts, can write `dump/<name>.zone` | `t7/zonetool.cpp` | written |
| Native image dump (`dumpzone t7 <zone>`): `images/<name>.dds` from loaded pixels or the largest streamed part in the xpaks, plus `<name>.t7image.json` | `t7/assets/gfximage.*` | written |
| Native material dump: `materials/<name>.t7material.json` (techset, textures with image semantic, constants, samplers) | `t7/assets/material.*` | written |
| BO3 -> H1 image: writes `images/<name>.dds`, which the H1 linker loads directly (`h1::directxtex::load_image`) | `t7/converter/h1/assets/gfximage.*` | written |
| BO3 -> H1 material: H1 material JSON on Ghosts `_iw6` techsets (world/model × opaque/blended, emissive, sky), picks the colour map by image semantic then name suffix; written after the whole zone is seen so materials used by xmodels get model techsets | `t7/converter/h1/assets/material.*` | written |
| `-dumpzone <target> <zone> [filter]` on the command line (was `t7` only) | `t7/zonetool.cpp` | written |
| `acts <args>` console command, and the `-dumpzone bo3 ... -acts-force` route through ACTS | `src/zonetool/acts/*` | written |

"Written" means syntax-checked on Linux with clang against the real `t7`/`h1` structs and stubbed
Windows headers. It has **not** been compiled with MSVC or run against real BO3 files.

### Unverified assumptions (check these first when testing)

- `GfxImage::streamedParts[i]` data in the xpak is the full mip chain for that part
  (`levelCount` levels starting at `width`×`height`, `pixelSize` bytes). The dumper picks the
  largest part and drops trailing mips if the data is short.
- Cubemaps: 6 faces × mips in D3D order; 2D arrays and cube arrays assume the array size is in `depth`.
- Loaded images: `pixels`/`totalSize` hold the whole chain when `streamedPartCount == 0`.
- Material camera regions -> blend mode: `GBUFFER_DECAL`/`DEPTH_HACK_DECAL` are decals,
  `LIT_TRANS*`/`OIT` translucent, `EMISSIVE_FX` additive. H1 sortKeys (2/7/24/53) copy the IW7 port.
- The `_iw6` techsets (`wc_l_sm_ndw_b0c0l0_nfwpf_iw6`, `mc_l_sm_r0c0n0s0l0_nfwpf_iw6`, ...) and the
  `blank` image must exist in the H1/HMW mod, as they do for the IW7 port.

### Stubbed / TODO

- BO3 -> H1 converters for **clipmap, comworld, gfxworld, mapents, weapons/attachments, fx, sounds**
  (marked TODO in `dump_asset_h1`). These are the bulk of map porting; the IW7 -> H1 versions in
  `iw7/converter/h1` are the template.
- Normal/gloss/spec maps in materials (BO3 normal maps are BC5, gloss separate); only colour is used.
- `surfaceTypeBits` mapping BO3 -> H1 (written as 0).
- Native reader: `.fd` patches, encrypted zones, full asset loading.

## How to test on the PC

BO3 files are in `C:\Users\Shadow\Documents\bo3_game_files`.

1. Build ZoneTool (`generate.bat`, then build `zonetool` in VS) from the `acts-integration` branch.
2. In-process (needs the BO3 Unranked Server from Steam: Library -> Tools ->
   "Call of Duty: Black Ops III - Unranked Server"):
   - copy `zonetool.exe` into the UnrankedServer folder; give it the client zones by copying or
     junctioning `bo3_game_files\zone` to `UnrankedServer\zone` (the xpak lookup checks `zone\` and
     `..\zone\`);
   - `zonetool.exe -ffinfo mp_sector` prints header + asset counts (offline reader check);
     compare the counts with `verifyzone mp_sector` in the console;
   - `zonetool.exe -dumpzone t7 mp_sector` gives native dumps in `dump\mp_sector\images\*.dds`
     and `materials\*.t7material.json`; open some DDS files (colour, normal, cubemap) to check them;
   - `zonetool.exe -dumpzone h1 mp_sector image,material,xmodel,xmodelmesh` gives the H1 set;
     copy it into an H1 zone source and `buildzone` with h1 ZoneTool, then check textures in game.
3. Through ACTS (any folder): build ACTS with `tools\build_acts.bat`, then
   `zonetool -acts game_dump bo3 "C:\...\bo3_game_files"` (once), then
   `zonetool -dumpzone bo3 "C:\...\bo3_game_files\zone\mp_sector.ff" -acts-force`
   to get rawfiles and GSC scripts in `dump\bo3\`.

## Next steps (priority order)

1. Test the steps above and fix whatever the first real run shows (image layout assumptions first).
2. BO3 -> H1 `gfxworld` + `clipmap` + `comworld` + `mapents` converters, porting the structure of
   `iw7/converter/h1/{gfxworld,clipmap,comworld,mapents}.cpp`. BO3 world vertex/index data is
   streamed from xpak like XModelMesh, so reuse `xpak::get_data_for_xpak_key`.
3. Material: use BO3 normal maps (BC5 -> H1 normal format) and pick techsets with normal mapping.
4. Weapons: BO3 weapondef/variant -> H1 weapon JSON (largest struct mapping job).
