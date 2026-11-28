# BO2 map -> H1/HMW look pipeline (per map)

1. Export from BO2 (codlegacyclient): map geometry/lightmap. Carrier's current lightmap (pass 9):
   `LM_CELLFLOOR=0.7 LM_SHADOWS=1 LM_KEEPSUN=1 LM_SUNSAT=1.0 LM_GAIN=0.30 LM_SAT=0.35 LM_FLOOR=0.35 build_h1_lightmap.py <h1map> <lmuv> lm0_s.raw props.tsv <prim template> <sec template> <out>`
   (LM_FLOOR 0.12 left baked shadows near black; 0.35 lifts them to ~15% of sunlit),
   ambience (`t6_map_ambient_export` -> `make_h1_sounds.py <export> <impact sounds> <out>`).
2. Vertex shadow/AO bake for static models: `bake_vertex_shadows.py <h1map> <lmuv> <map>_vcol.bin [sun dir]` -> `bo2_import/<map>/<map>_vcol.bin`.
3. Art: fog.txt / vision.txt from `maps/mp/<map>_art.gsc` + vision file (fog intensity 11, opacity <=0.8; lit HDR scalar 0.55).
4. Water: `h1_imports.txt` (`material techsets_mp_cargoship mc/h1_mp_cargoship_ocean_a mp_cargoship`, `xmodel mp_cargoship cargoship_water_mp`) + `h1_models.txt` placement at sea level.
5. Patch + build: `carrier_look_patch.ps1` (LOOK_SUN etc.) then `waw_port.ps1 -Map <map> -Src <src>`.
6. Sky sun: `sky_sun.py <sky.dds> <out.dds> sx sy sz [band 1.5] [halo 0.45]` (H1 samples the cube with world xyz, D3D face rules).
7. Reflection probe: replace the mp_flip placeholder with a 64x64 RGBA8 cube from the sky (bo2_import/<map>/lightmap/_reflection_probe0.h1Image).
8. Blend layers: bo2_h1_export (codlegacyclient 86215e1+) writes BO2 blend layers as decal surfaces `<layer>_bo2layer` (vertex alpha = weight).
   Missing pictures: H1_EXPORT_LIST_MISSING=1 lists them; pull the ranges out of base.ipak on the PC (ipak_bundle.ps1) and fill a sparse base.ipak.
9. Debug: `pick.py <h1map> x y z yaw pitch ...` prints the surface/material a view ray hits.
10. Hull macro grime (ship maps): `make_hull_grime_tex.py` -> hull_grime.png (BC3 sRGB as `ghull_grime_macro_c`),
    `add_grime.py <h1map> <lmuv> <h1lmuv> <vcol.bin> <out> <hull material substrings> [top_z height tile]` adds the decal surfaces
    and extends the side files; add `wpc/hull_grime_macro_bo2layer	2	ghull_grime_macro_c	-	-	-` to mats.tsv.
11. Sea haze (water shaders ignore fog): `add_haze_ring.py <out dir> <stem> cx cy z r0 r1 rmax` (z ~20 above the sea),
    mats.tsv `wpc/sea_haze_ring_bo2layer	2	ghaze_ring_c	-	-	-`.
12. Live fog: `set port_f0..f7 ...;set port_fogn 108` then press Return separately (H1 HDR intensity 11; 13+ whites out).
13. Materials: `make_default_specs.py <mats.tsv> <colour dds dir> <out dir> <out mats.tsv>` gives every opaque material without a
    specular picture an H1 one (rgb spec, alpha gloss; level by name keywords, gloss varies with the colour). The exporter's own
    `_s` pictures already carry BO2's gloss in alpha.
14. Sky: `bo2_sky_to_h1.py <raw sky bytes> <header dds> <out dds>`: BO2's own sky cube (identity face mapping, rgb*alpha*0.62),
    lower half = horizon colour fading to haze. Also write it x1.8 as `hdr_h1_sky_cargoshipocean_ft.dds` (the Wet Work ocean's
    reflection) and as `_reflection_probe0.h1Image`.
15. Probes: codlegacyclient `t6_probe_dump <ff> <out>` -> BO2 probes (BC3 RGBM 128 cubes) -> `_reflection_probe<N>.h1Image`
    (64x64 RGBA8, 7 mips, alpha 66) in `bo2_import\<map>\lightmap` plus `<map>.probes`; ZoneTool 092ed06 assigns the nearest
    probe (3000 units) per surface. `<map>.grid` "r g b" sets the flat light grid for models.
16. Effects: `bo2_fx_place.py <createfx.tsv> bo2_fx_map.tsv <out>` writes fx_place.txt + fx_imports.txt from the shared table.
17. Props: codlegacyclient `t6_smodel_dump <ff>` + `bo2_props.py` swap BO2 static models for same-name MWR models (upright only).
    Carrier: only 30 pipe couplings qualify; not enabled (their materials need importing too).
18. Ocean: keep the Wet Work model (`h1_models.txt`) and put Beach Bog's ocean pictures into the zone too (from
    dump\mp_bog_summer\images); with them in the zone the Wet Work ocean shows foam and wave detail (r32). The run bat copies
    `h1_mp_bog_summer_waterripple_nml, h1_ocean_waves_bog_summer_nml, h1_bog_summer_ocean_color, ocean_generic_foam, h1_ocean_foam_1_col`
    into `zonetool\bogsea\images`, plus the bog techsets (and flattens state/constantbuffer `\wc`) for the `bo2_sea` swap.
    Beach Bog's own ocean on our world sea (LOOK_NOSEA unset) still renders black even with all pictures and stock-style surface data
    (ZoneTool ffe6c1d): open problem, see the project doc.
19. ZoneTool importer (607128b): every surface gets its longest edge (`maxEdgeLength`), its texture density in |binormalSign|
    (stock H1 vertices carry texture units per world unit there), opaque surfaces the sun-shadow flag, ocean surfaces env 0 / flag 4.
    The run bat downloads `Release.zonetool.zip` from the `latest` release into `zonetool_new.exe` (old build kept as zonetool_b11.exe).
20. Model lighting (ZoneTool 1a0a157): `<stem>.grid56` (56 "r g b" lines) gives models directional light. Make it with
    codlegacyclient `t6_grid_dump <ff> <dir>` (copy `t6_grid_dump.rs` into crates/asset_t6/examples) then
    `grid56_from_bo2.py <dir> mp_carrier.grid56 0.75 0.70 0.64`. Carrier's grid is SH only (0 colour sets, 47408 coefficient sets).
21. Blend-layer specs: `fix_blend_specs.py <mats.tsv> <out>`: the exporter can give a layered surface a decal layer's spec
    (the deck under me_oilstain came out as a glossy charcoal block); this resets those rows to the base layer's spec.
22. Ocean reflection cube: `ocean/make_ocean_reflection_cube.py` turns the Carrier skybox (512 RGBA8 cube) into the 1024 BC6H
    cube `hdr_h1_sky_cargoshipocean_ft` (cube faces in D3D order, z up; a sun lobe toward the map's sun, horizon band in the fog
    colour), encoder in `ocean/bc6enc` (intel_tex_2; also `bc3dds` and `bc1mips`). `ocean_generic_color` (256 BC1 gradient)
    lifted 1.7x toward grey. Both overwrite dump\mp_cargoship\images (originals kept as .orig).
23. Collision (ZoneTool 3010a4f + fix): `<stem>.col` from codlegacyclient `t6_col_dump <ff> <dir> <stem>` (copy
    `t6_col_dump.rs` into crates/asset_t6/examples) replaces the render-triangle collision: BO2's own clip mesh, its world
    brushes (solid / player clip) turned into triangles, and an oriented box per static-model collision surface, written as plain solid (contents 1) and bullet-only clip left out: with BO2's contents passed
    through (COL_FULL=1) H1 players fell through everything. Brushes over 9000 units (whole-map volumes) and triangles with
    edges over 16000 (the sea plane) are dropped: they break the H1 collision tree. Carrier: ~72k triangles, nothing dropped (the old path kept 170k of ~3M render triangles and lost the stairs). `BO2_COL_RENDER=1`
    goes back to render triangles.
24. Pictures the map zone only names (0x0, "," prefix, e.g. the drone body, the jets' normal maps):
    `t6_missing_images <ff>` lists them with their pack name hashes; `ipak_pull.ps1 -Dir bo2_game_files\zone\all -Out ...
    -Hashes ...` pulls them on the PC; `t6_stored_iwi` decodes level 0; `ocean/bc6enc` `dds_mips <raw> <dds> w h 72|78|83`
    writes the DX10 DDS (BC1 sRGB / BC3 sRGB / BC5) the importer reads. Then point the mats.tsv rows at them.
