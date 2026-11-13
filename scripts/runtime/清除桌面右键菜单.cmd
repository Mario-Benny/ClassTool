@echo off
setlocal EnableExtensions

set "SILENT=0"
if /I "%~1"=="/silent" set "SILENT=1"
set "APP_DIR=%~dp0"

tasklist /FI "IMAGENAME eq ClassTool.exe" 2>nul | find /I "ClassTool.exe" >nul
if not errorlevel 1 (
    echo [ERROR] Exit ClassTool completely before changing its context menu.
    if "%SILENT%"=="0" pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root='HKCU:\Software\Classes\DesktopBackground\shell\ClassTool'; if(Test-Path $root){Remove-Item $root -Recurse -Force}; $settings=Join-Path $env:APP_DIR 'data\settings.json'; if(Test-Path -LiteralPath $settings){$data=Get-Content -LiteralPath $settings -Raw -Encoding UTF8 | ConvertFrom-Json; if($null -eq $data){$data=[pscustomobject]@{}}}else{$data=[pscustomobject]@{}}; New-Item -ItemType Directory -Path (Split-Path $settings) -Force | Out-Null; $data | Add-Member -NotePropertyName 'context_menu_enabled' -NotePropertyValue $false -Force; [IO.File]::WriteAllText($settings,($data | ConvertTo-Json -Depth 10),(New-Object Text.UTF8Encoding $true))"

if errorlevel 1 (
    echo [ERROR] Failed to remove the ClassTool desktop context menu.
    if "%SILENT%"=="0" pause
    exit /b 1
)

echo [OK] The ClassTool desktop context menu was removed.
if "%SILENT%"=="0" pause
exit /b 0
