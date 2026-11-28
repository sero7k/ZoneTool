@echo off
rem (run29: run28 + latest ZoneTool release (directional light grid from mp_carrier.grid56)) Carrier: update ZoneTool, unpack, rebuild, start the game.
cd /d "%~dp0"
taskkill /f /im "Cod Legacy.exe" >NUL 2>&1
taskkill /f /im zonetool_new.exe >NUL 2>&1
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/sero7k/ZoneTool/releases/download/latest/Release.zonetool.zip' -OutFile '%~dp0zt_release.zip'; Remove-Item -Recurse -Force '%~dp0zt_release' -ErrorAction SilentlyContinue; Expand-Archive -Path '%~dp0zt_release.zip' -DestinationPath '%~dp0zt_release' -Force; $e = Get-ChildItem '%~dp0zt_release' -Recurse -Filter zonetool.exe | Select-Object -First 1; if ($e) { Copy-Item $e.FullName '%~dp0zonetool_new.exe' -Force; 'zonetool updated ' + $e.Length | Out-File '%~dp0zt_update.log' } else { 'no zonetool.exe in release' | Out-File '%~dp0zt_update.log' }"
echo started> "%~dp0carrier_light.done"
cd /d "%~dp0"
set C=bo2_import\carrier
if not exist "%C%\mp_carrier.h1map.orig.v1" copy /y "%C%\mp_carrier.h1map.orig" "%C%\mp_carrier.h1map.orig.v1" >NUL
if not exist "%C%\mp_carrier.mats.tsv.v1" copy /y "%C%\mp_carrier.mats.tsv" "%C%\mp_carrier.mats.tsv.v1" >NUL
if exist "%C%\h1map_layers.zip.part00" (
  copy /b "%C%\h1map_layers.zip.part00"+"%C%\h1map_layers.zip.part01"+"%C%\h1map_layers.zip.part02" "%C%\h1map_layers.zip" >NUL
  powershell -NoProfile -Command "Expand-Archive -Path '%~dp0bo2_import\carrier\h1map_layers.zip' -DestinationPath '%~dp0bo2_import\carrier' -Force"
  del "%C%\h1map_layers.zip.part0*" "%C%\h1map_layers.zip"
)
if exist "%C%\mp_carrier.h1map.layers" move /y "%C%\mp_carrier.h1map.layers" "%C%\mp_carrier.h1map.orig" >NUL
if exist "%C%\mp_carrier.mats.tsv.layers" move /y "%C%\mp_carrier.mats.tsv.layers" "%C%\mp_carrier.mats.tsv" >NUL
if not exist "bo2_import\carrier\lightmap" mkdir "bo2_import\carrier\lightmap"
powershell -NoProfile -Command "Expand-Archive -Path '%~dp0bo2_import\carrier\carrier_lightmap.zip' -DestinationPath '%~dp0bo2_import\carrier\lightmap' -Force"
move /y "bo2_import\carrier\lightmap\mp_carrier.h1lmuv" "bo2_import\carrier\mp_carrier.h1lmuv" >NUL
powershell -NoProfile -Command "Expand-Archive -Path '%~dp0bo2_import\carrier\carrier_sounds.zip' -DestinationPath '%~dp0bo2_import\carrier' -Force"
if not exist "zonetool\bogsea\materials\wc" mkdir "zonetool\bogsea\materials\wc"
copy /y "dump\techsets_mp_bog_summer\materials\wc\h1_mp_bog_summer_ocean_01.json" "zonetool\bogsea\materials\wc\h1_mp_bog_summer_ocean_01.json" >NUL
powershell -NoProfile -Command "$s='%~dp0dump\mp_bog_summer'; $d='%~dp0zonetool\bogsea'; foreach ($n in @('h1_mp_bog_summer_waterripple_nml','h1_ocean_waves_bog_summer_nml','h1_bog_summer_ocean_color','ocean_generic_foam','h1_ocean_foam_1_col')) { foreach ($sub in @('images','streamed_images')) { if (Test-Path \"$s\$sub\") { New-Item -ItemType Directory -Force -Path \"$d\$sub\" | Out-Null; Get-ChildItem -LiteralPath \"$s\$sub\" -File -Filter \"$n*\" | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination \"$d\$sub\" -Force; Add-Content '%~dp0bogsea_images.log' $_.Name } } } }"
set T=wc_ocean_nolm_displace_hrzn_octave3_addhght3_foam2_gloss_ssr_detail_cltrans_hdr
robocopy "dump\techsets_mp_bog_summer\techsets" "zonetool\bogsea\techsets" /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP >NUL
robocopy "dump\techsets_mp_bog_summer\dumped_techsets" "zonetool\bogsea\dumped_techsets" /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP >NUL
for %%K in (state constantbuffer) do if exist "zonetool\bogsea\techsets\%%K\%T%\wc" for %%F in ("zonetool\bogsea\techsets\%%K\%T%\wc\*") do copy /y "%%F" "zonetool\bogsea\techsets\%%K\%T%\" >NUL
powershell -NoProfile -Command "Expand-Archive -Path '%~dp0bo2_import\carrier\carrier_specs.zip' -DestinationPath '%~dp0bo2_import\carrier\images' -Force"
set LOOK_SUN=2.4 2.15 1.6
set LOOK_NOSEA=1
set LOOK_NOWATER=1
set LOOK_SEAUV=6
set LOOK_SEALMV=147711
set LOOK_SKIPMAT=quad_rotor_blades_dead,decal_sdc_logo_bo2layer,concrete_burnt_blend_bo2layer,decal_wires1_bo2layer,me_oilstain_bo2layer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0carrier_look_patch.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0waw_port.ps1" -Map mp_carrier -Src carrier -Inter "-5961 1363 600" -InterAng "25 350 0"
copy /y waw_port.log carrier_port.log >NUL
echo built> "%~dp0carrier_light.done"
start "" "Cod Legacy.exe"
