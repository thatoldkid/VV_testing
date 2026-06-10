@echo off
setlocal

:: Rebuilds dist\VibrantVisuals.mcaddon (validates all JSON) and opens it
:: with Minecraft's importer. Use deploy.bat instead for fast iteration.

pushd "%~dp0"
python build_mcaddon.py
if errorlevel 1 (
    echo [ERROR] build failed - .mcaddon not updated.
    popd
    exit /b 1
)
start "" "dist\VibrantVisuals.mcaddon"
popd
