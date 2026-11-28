# Carrier handoff (2026-11-28)

Files made in the cloud session after `claude_port.zip` was packed on the Shadow PC. Copy them over the unzipped tree on the new PC:

- `bo2_import_carrier/*` -> `Documents\mwr_game_files\bo2_import\carrier\` (mp_carrier.col = BO2 collision, mp_carrier.mats.tsv = blend-spec fix + jet/drone textures, vision_a..d = brightness steps, fx_place.txt = hull foam wakes, carrier_run29.bat/next.bat = build bats)
- `bo2_import_carrier/images/*_bo2pull.dds` -> `...\bo2_import\carrier\images\`
- `bo2_import_carrier/hdr_h1_sky_cargoshipocean_ft.h1Image`, `ocean_generic_color.h1Image` -> `Documents\mwr_game_files\dump\mp_cargoship\images\`
- `bo2_import_carrier/h1_mp_cargoship_ocean_a.json` -> `Documents\mwr_game_files\dump\techsets_mp_cargoship\materials\mc\`
- `bo2tools/*` -> `Documents\mwr_game_files\bo2tools\` (README steps 1-24)
- `codlegacyclient_examples/*.rs` -> codlegacyclient `crates/asset_t6/examples/`

Paths in the bats/ps1 assume `C:\Users\Shadow`; on the Hetzner PC the user is `sero`.
See the project doc `claude/bo2-carrier-handoff-2026-11-28.md`.
