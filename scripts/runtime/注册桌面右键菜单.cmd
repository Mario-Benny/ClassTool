@echo off
setlocal EnableExtensions

set "SILENT=0"
if /I "%~1"=="/silent" set "SILENT=1"
set "APP_DIR=%~dp0"
set "TARGET=%~dp0ClassTool.exe"

if not exist "%TARGET%" (
    echo [ERROR] ClassTool.exe was not found beside this script.
    if "%SILENT%"=="0" pause
    exit /b 1
)

tasklist /FI "IMAGENAME eq ClassTool.exe" 2>nul | find /I "ClassTool.exe" >nul
if not errorlevel 1 (
    echo [ERROR] Exit ClassTool completely before changing its context menu.
    if "%SILENT%"=="0" pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; function U([int[]]$c){return -join ($c | ForEach-Object {[char]$_})}; $settings=Join-Path $env:APP_DIR 'data\settings.json'; if(Test-Path -LiteralPath $settings){$data=Get-Content -LiteralPath $settings -Raw -Encoding UTF8 | ConvertFrom-Json; if($null -eq $data){$data=[pscustomobject]@{}}}else{$data=[pscustomobject]@{}}; $root='HKCU:\Software\Classes\DesktopBackground\shell\ClassTool'; if(Test-Path $root){Remove-Item $root -Recurse -Force}; New-Item $root -Force | Out-Null; New-ItemProperty $root -Name 'MUIVerb' -Value 'ClassTool' -PropertyType String -Force | Out-Null; New-ItemProperty $root -Name 'SubCommands' -Value '' -PropertyType String -Force | Out-Null; New-ItemProperty $root -Name 'Icon' -Value ($env:TARGET+',0') -PropertyType String -Force | Out-Null; $container=Join-Path $root 'shell'; New-Item $container -Force | Out-Null; $items=@(@('01_calculator_tool',(U @(0x7B80,0x6613,0x8BA1,0x7B97,0x5668)),'calculator_tool'),@('02_countdown_timer',(U @(0x5012,0x8BA1,0x65F6,0x88C5,0x7F6E)),'countdown_timer'),@('03_document_camera_tool',(U @(0x5C55,0x53F0)),'document_camera_tool'),@('04_random_picker',(U @(0x968F,0x673A,0x70B9,0x540D,0x5668)),'random_picker'),@('05_screen_doodle_tool',(U @(0x6D82,0x9E26,0x6A21,0x5757)),'screen_doodle_tool'),@('06_voting_tool',(U @(0x6295,0x7968,0x6A21,0x5757)),'voting_tool')); $quote=[char]34; $count=0; foreach($item in $items){$plugin=Join-Path $env:APP_DIR ('tools\'+$item[2]+'.py'); if(Test-Path -LiteralPath $plugin){$itemKey=Join-Path $container $item[0]; New-Item $itemKey -Force | Out-Null; New-ItemProperty $itemKey -Name 'MUIVerb' -Value $item[1] -PropertyType String -Force | Out-Null; $commandKey=Join-Path $itemKey 'command'; New-Item $commandKey -Force | Out-Null; Set-Item -Path $commandKey -Value ($quote+$env:TARGET+$quote+' --tool '+$quote+$item[2]+$quote); $count++}}; if($count -eq 0){Remove-Item $root -Recurse -Force; throw 'No official plugins were found'}; New-Item -ItemType Directory -Path (Split-Path $settings) -Force | Out-Null; $data | Add-Member -NotePropertyName 'context_menu_enabled' -NotePropertyValue $true -Force; [IO.File]::WriteAllText($settings,($data | ConvertTo-Json -Depth 10),(New-Object Text.UTF8Encoding $true)); Write-Output $count"

if errorlevel 1 (
    echo [ERROR] Failed to register the ClassTool desktop context menu.
    if "%SILENT%"=="0" pause
    exit /b 1
)

echo [OK] The ClassTool desktop context menu was registered.
if "%SILENT%"=="0" pause
exit /b 0
