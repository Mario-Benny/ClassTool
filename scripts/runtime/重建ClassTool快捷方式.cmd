@echo off
setlocal EnableExtensions

set "APP_DIR=%~dp0"
set "TARGET=%~dp0ClassTool.exe"
set "UNINSTALL=%~dp0uninstall.exe"

if not exist "%TARGET%" (
    echo [ERROR] ClassTool.exe was not found beside this script.
    pause
    exit /b 1
)
if not exist "%UNINSTALL%" (
    echo [ERROR] uninstall.exe was not found. Run this script after installation.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $shell=New-Object -ComObject WScript.Shell; $working=$env:APP_DIR.TrimEnd('\'); function New-Link([string]$path,[string]$target,[string]$description){$shortcut=$shell.CreateShortcut($path); $shortcut.TargetPath=$target; $shortcut.WorkingDirectory=$working; $shortcut.IconLocation=$target+',0'; $shortcut.Description=$description; $shortcut.Save()}; $desktop=[Environment]::GetFolderPath('Desktop'); $programs=[Environment]::GetFolderPath('Programs'); $folder=Join-Path $programs 'ClassTool'; $uninstallName=(-join @([char]0x5378,[char]0x8F7D))+' ClassTool.lnk'; New-Item -ItemType Directory -Path $folder -Force | Out-Null; New-Link (Join-Path $desktop 'ClassTool.lnk') $env:TARGET 'ClassTool'; New-Link (Join-Path $programs 'ClassTool.lnk') $env:TARGET 'ClassTool'; New-Link (Join-Path $folder 'ClassTool.lnk') $env:TARGET 'ClassTool'; New-Link (Join-Path $folder $uninstallName) $env:UNINSTALL 'Uninstall ClassTool'"

if errorlevel 1 (
    echo [ERROR] Failed to rebuild ClassTool shortcuts.
    pause
    exit /b 1
)

echo [OK] Desktop and Start menu shortcuts were rebuilt.
pause
exit /b 0
