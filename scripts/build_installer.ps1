$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$AppRoot = Join-Path $Root 'src\ClassTool'
$ReleaseRoot = Join-Path $Root 'release'
$RuntimeScripts = Join-Path $PSScriptRoot 'runtime'
$Nsi = Join-Path $PSScriptRoot 'nsis\ClassTool.nsi'
$Verifier = Join-Path $PSScriptRoot 'nsis\verify_toolchain.ps1'
$DistRoot = Join-Path $PSScriptRoot 'dist'
$WorkRoot = Join-Path $PSScriptRoot 'build'
$Payload = Join-Path $WorkRoot 'payload'
$PyWork = Join-Path $WorkRoot 'pyinstaller'
$SpecPath = Join-Path $WorkRoot 'spec'
$WindowsPowerShell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$Icon = Join-Path $Root 'assets\logo.ico'
$VersionJson = Join-Path $AppRoot 'version.json'

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) { throw 'Python was not found in PATH' }
$Python = $PythonCommand.Source

$MakensisCommand = Get-Command makensis -ErrorAction SilentlyContinue
$NsisRegistryRoot = $null
foreach ($registryPath in @(
    'HKLM:\SOFTWARE\NSIS',
    'HKLM:\SOFTWARE\WOW6432Node\NSIS',
    'HKCU:\SOFTWARE\NSIS'
)) {
    if (Test-Path -LiteralPath $registryPath) {
        $NsisRegistryRoot = (Get-ItemProperty -LiteralPath $registryPath).'(default)'
        if ($NsisRegistryRoot) { break }
    }
}
$MakensisCandidates = @(
    $(if ($null -ne $MakensisCommand) { $MakensisCommand.Source }),
    $(if ($env:NSIS_HOME) { Join-Path $env:NSIS_HOME 'makensis.exe' }),
    $(if ($NsisRegistryRoot) { Join-Path $NsisRegistryRoot 'makensis.exe' }),
    $(if (${env:ProgramFiles(x86)}) { Join-Path ${env:ProgramFiles(x86)} 'NSIS\makensis.exe' }),
    $(if ($env:ProgramFiles) { Join-Path $env:ProgramFiles 'NSIS\makensis.exe' })
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
if ($MakensisCandidates.Count -eq 0) { throw 'NSIS makensis.exe was not found' }
$Makensis = $MakensisCandidates[0]

foreach ($p in @($ReleaseRoot, $DistRoot, $WorkRoot, $PyWork, $SpecPath)) {
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}
if (Test-Path -LiteralPath $Payload) { Remove-Item -LiteralPath $Payload -Recurse -Force }
New-Item -ItemType Directory -Path $Payload | Out-Null

if (-not (Test-Path -LiteralPath $Icon)) { throw "Icon not found: $Icon" }

$Version = (Get-Content -LiteralPath $VersionJson -Raw -Encoding UTF8 | ConvertFrom-Json).version
if ([string]::IsNullOrWhiteSpace($Version)) { throw "version.json has no version" }
$parts = $Version.Split('.')
while ($parts.Count -lt 4) { $parts += '0' }
$FileVersion = ($parts[0..3] -join '.')

$Installer = Join-Path $ReleaseRoot "ClassTool-v$Version-Setup.exe"

Write-Host "[1/4] Verify NSIS toolchain ..."
& $WindowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $Verifier -Makensis $Makensis
if ($LASTEXITCODE -ne 0) { throw "NSIS toolchain verification failed" }

Write-Host "[2/4] PyInstaller onedir build ..."
foreach ($name in @('ClassTool.exe', '_internal', 'ClassTool', 'tools')) {
    $p = Join-Path $Payload $name
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Recurse -Force
    }
}

$pyArgs = @(
    '-m', 'PyInstaller',
    '--noconfirm', '--clean', '--onedir', '--windowed',
    '--name', 'ClassTool',
    '--icon', $Icon,
    '--add-data', "$(Join-Path $AppRoot 'language');language",
    '--add-data', "${VersionJson};.",
    '--hidden-import', 'PySide6.QtNetwork',
    '--hidden-import', 'PySide6.QtMultimedia',
    '--hidden-import', 'PySide6.QtMultimediaWidgets',
    '--distpath', $DistRoot,
    '--workpath', $PyWork,
    '--specpath', $SpecPath,
    (Join-Path $AppRoot 'main.py')
)
$pyLog = Join-Path $WorkRoot 'pyinstaller.log'
$pyOut = Join-Path $WorkRoot 'pyinstaller.stdout.log'
$pyErr = Join-Path $WorkRoot 'pyinstaller.stderr.log'
$originalPath = $env:PATH
$pythonRoot = Split-Path -Parent $Python
$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$env:PATH = (@($pythonRoot, (Join-Path $pythonRoot 'Scripts'), $machinePath, $userPath) -join ';')
try {
    # Codex 自身 PATH 含 Poppler/ICU 等开发工具 DLL。若让 PyInstaller 看见它们，
    # 依赖分析会把非应用依赖误收进发行包，导致离开开发终端后 QtCore 无法加载。
    $pyProc = Start-Process -FilePath $Python -ArgumentList $pyArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $pyOut -RedirectStandardError $pyErr
} finally {
    $env:PATH = $originalPath
}
$pyText = (Get-Content -LiteralPath $pyOut -Raw -ErrorAction SilentlyContinue) + "`r`n" + (Get-Content -LiteralPath $pyErr -Raw -ErrorAction SilentlyContinue)
[IO.File]::WriteAllText($pyLog, $pyText, (New-Object Text.UTF8Encoding $false))
if ($pyProc.ExitCode -ne 0) { throw "PyInstaller failed ($($pyProc.ExitCode)), see $pyLog" }

$BuiltDir = Join-Path $DistRoot 'ClassTool'
$BuiltExe = Join-Path $BuiltDir 'ClassTool.exe'
if (-not (Test-Path -LiteralPath $BuiltExe)) { throw "PyInstaller output missing: $BuiltExe" }

$QtNet = Get-ChildItem -LiteralPath $BuiltDir -Recurse -Filter 'Qt6Network.dll' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $QtNet) { throw "Qt6Network.dll not bundled" }
$BundleVersion = Get-ChildItem -LiteralPath $BuiltDir -Recurse -Filter 'version.json' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $BundleVersion) { throw "version.json not bundled" }
$BundleLanguage = Get-ChildItem -LiteralPath $BuiltDir -Recurse -Filter 'zh_CN.json' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $BundleLanguage) { throw "language/zh_CN.json not bundled" }

Write-Host "  Qt6Network: $($QtNet.FullName)"
Write-Host "  version.json: $($BundleVersion.FullName)"
Write-Host "  language: $($BundleLanguage.FullName)"

Write-Host "[3/4] Populate payload ..."
Get-ChildItem -LiteralPath $BuiltDir -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Payload -Recurse -Force
}

$ToolsDest = Join-Path $Payload 'tools'
if (-not (Test-Path -LiteralPath $ToolsDest)) { New-Item -ItemType Directory -Path $ToolsDest | Out-Null }
$BuiltinTools = @(
    'calculator_tool.py',
    'countdown_timer.py',
    'document_camera_tool.py',
    'random_picker.py',
    'screen_doodle_tool.py',
    'voting_tool.py'
)
foreach ($tool in $BuiltinTools) {
    $src = Join-Path $AppRoot "tools\$tool"
    if (-not (Test-Path -LiteralPath $src)) { throw "Tool missing: $src" }
    Copy-Item -LiteralPath $src -Destination $ToolsDest -Force
}

New-Item -ItemType Directory -Path (Join-Path $Payload 'data') -Force | Out-Null
foreach ($scriptName in @(
    '重建ClassTool快捷方式.cmd',
    '注册桌面右键菜单.cmd',
    '清除桌面右键菜单.cmd'
)) {
    $scriptPath = Join-Path $RuntimeScripts $scriptName
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Runtime script missing: $scriptPath" }
    Copy-Item -LiteralPath $scriptPath -Destination $Payload -Force
}

foreach ($required in @(
    'ClassTool.exe',
    '_internal',
    'tools',
    'data',
    '重建ClassTool快捷方式.cmd',
    '注册桌面右键菜单.cmd',
    '清除桌面右键菜单.cmd'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $Payload $required))) { throw "Payload missing: $required" }
}

$manifest = Get-ChildItem -LiteralPath $Payload -Recurse -File | ForEach-Object {
    $_.FullName.Substring($Payload.Length + 1)
}
[IO.File]::WriteAllText((Join-Path $DistRoot 'payload-files.txt'), (($manifest -join "`r`n") + "`r`n"), (New-Object Text.UTF8Encoding $false))

Write-Host "[4/4] makensis ..."
$mkLog = Join-Path $WorkRoot 'makensis.log'
$mkOut = Join-Path $WorkRoot 'makensis.stdout.log'
$mkErr = Join-Path $WorkRoot 'makensis.stderr.log'
$mkArgs = @('/V2', "/DVERSION=$Version", "/DFILEVERSION=$FileVersion", "/DPAYLOAD=$Payload", "/DOUTFILE=$Installer", "/DICON=$Icon", $Nsi)
$mkProc = Start-Process -FilePath $Makensis -ArgumentList $mkArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $mkOut -RedirectStandardError $mkErr
$mkText = (Get-Content -LiteralPath $mkOut -Raw -ErrorAction SilentlyContinue) + "`r`n" + (Get-Content -LiteralPath $mkErr -Raw -ErrorAction SilentlyContinue)
[IO.File]::WriteAllText($mkLog, $mkText, (New-Object Text.UTF8Encoding $false))
if ($mkProc.ExitCode -ne 0) { throw "makensis failed ($($mkProc.ExitCode)), see $mkLog" }
if (-not (Test-Path -LiteralPath $Installer)) { throw "Installer not created: $Installer" }

$item = Get-Item -LiteralPath $Installer
$hash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$Installer.sha256", "$hash  $($item.Name)`r`n", (New-Object Text.UTF8Encoding $false))

$UpdateManifest = Join-Path $ReleaseRoot 'update.json'
$manifest = [ordered]@{
    schema_version = 1
    version = $Version
    minimum_updater_version = '1.0.0'
    channel = 'stable'
    mandatory = $false
    published_at = (Get-Date -Format 'yyyy-MM-dd')
    installer = [ordered]@{
        name = $item.Name
        url = "https://github.com/Mario-Benny/ClassTool/releases/download/v$Version/$($item.Name)"
        size = $item.Length
        sha256 = $hash
    }
    release_notes_url = "https://github.com/Mario-Benny/ClassTool/releases/tag/v$Version"
}
$manifestJson = $manifest | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText($UpdateManifest, "$manifestJson`r`n", (New-Object Text.UTF8Encoding $false))

Write-Host ""
Write-Host "BUILD OK"
Write-Host "  Version:      $Version ($FileVersion)"
Write-Host "  Payload:      $Payload"
Write-Host "  Installer:    $Installer"
Write-Host "  Size:         $($item.Length) bytes"
Write-Host "  FileVersion:  $($item.VersionInfo.FileVersion)"
Write-Host "  SHA256:       $hash"
Write-Host "  Update JSON:  $UpdateManifest"
