@echo off
rem Builds atian-cod-tools (ACTS) from deps\atian-cod-tools and copies acts.exe + its DLLs/data
rem into build\bin\x64\Release\acts\ so the ZoneTool ACTS bridge finds it next to zonetool.exe.
rem
rem Requirements (same as upstream ACTS): Visual Studio 2026 (v143 toolset), CMake 3.26+, git.
rem vcpkg is bundled as an ACTS submodule; the first configure downloads its packages (slow).
rem
rem Usage: tools\build_acts.bat [output dir]

setlocal
pushd "%~dp0.."

set "OUT=%~1"
if "%OUT%"=="" set "OUT=build\bin\x64\Release\acts"

rem the submodule is marked "update = none" so normal generate.bat runs skip it
git -c submodule.deps/atian-cod-tools.update=checkout submodule update --init deps/atian-cod-tools || goto :error
git -C deps\atian-cod-tools submodule update --init --recursive || goto :error

pushd deps\atian-cod-tools
rem the "gpl" preset enables the GPL-only parts (IW-engine gsc via xensik/gsc-tool);
rem ZoneTool is GPL-3 so the GPL build is the right one
if not exist vcpkg\vcpkg.exe call vcpkg\bootstrap-vcpkg.bat -disableMetrics || goto :error_acts
cmake --preset gpl || goto :error_acts
cmake --build build --config Release --parallel || goto :error_acts
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\copydata.ps1
popd

if not exist "%OUT%" mkdir "%OUT%"
xcopy /y /e /i /q "deps\atian-cod-tools\build\bin\Release\*" "%OUT%\" >nul || goto :error
xcopy /y /e /i /q "deps\atian-cod-tools\licenses" "%OUT%\licenses\" >nul
copy /y "deps\atian-cod-tools\LICENSE.md" "%OUT%\LICENSE.md" >nul

echo ACTS built into %OUT%
popd
endlocal
exit /b 0

:error_acts
popd
:error
echo ACTS build failed
popd
endlocal
exit /b 1
