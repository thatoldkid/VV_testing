@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  Vibrant Visuals - deploy packs straight into Minecraft
::
::  Usage:
::    deploy.bat            -> retail Minecraft (Bedrock)
::    deploy.bat preview    -> Minecraft Preview
::
::  Copies packs\VibrantVisualsRP and packs\VibrantVisualsBP into
::  the com.mojang development pack folders, so they show up under
::  "My Packs" immediately - no .mcaddon import or version bump
::  needed. Re-run after any change, then reload your world.
:: ============================================================

set "PKG=Microsoft.MinecraftUWP_8wekyb3d8bbwe"
set "EDITION=Minecraft (retail)"
if /i "%~1"=="preview" (
    set "PKG=Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe"
    set "EDITION=Minecraft Preview"
)

set "COM_MOJANG=%LOCALAPPDATA%\Packages\%PKG%\LocalState\games\com.mojang"

if not exist "%COM_MOJANG%" (
    echo [ERROR] Could not find %EDITION% data folder:
    echo         %COM_MOJANG%
    echo.
    echo Make sure %EDITION% is installed and has been launched at
    echo least once. For Minecraft Preview, run:  deploy.bat preview
    exit /b 1
)

set "RP_DEST=%COM_MOJANG%\development_resource_packs\VibrantVisualsRP"
set "BP_DEST=%COM_MOJANG%\development_behavior_packs\VibrantVisualsBP"

echo Deploying to %EDITION% ...
echo.

robocopy "%~dp0packs\VibrantVisualsRP" "%RP_DEST%" /MIR /NFL /NDL /NJH /NJS /NP
if errorlevel 8 goto :copyfail
echo   [OK] resource pack  ^>  %RP_DEST%

robocopy "%~dp0packs\VibrantVisualsBP" "%BP_DEST%" /MIR /NFL /NDL /NJH /NJS /NP
if errorlevel 8 goto :copyfail
echo   [OK] behavior pack  ^>  %BP_DEST%

echo.
echo Done! Packs are under "My Packs" in the world's pack lists.
echo If Minecraft was already in a world, leave and re-enter it to
echo pick up the changes.
exit /b 0

:copyfail
echo.
echo [ERROR] robocopy failed (exit code %ERRORLEVEL%). Is Minecraft
echo running and locking the files? Close it and try again.
exit /b 1
