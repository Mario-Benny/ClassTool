param(
    [string]$Makensis
)

$ErrorActionPreference = 'Stop'

function Stop-WithFailure {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[ OK ] $Message" -ForegroundColor Green
}

if ([string]::IsNullOrWhiteSpace($Makensis)) {
    $command = Get-Command makensis -ErrorAction SilentlyContinue
    $candidates = @(
        $(if ($null -ne $command) { $command.Source }),
        $(if (${env:ProgramFiles(x86)}) { Join-Path ${env:ProgramFiles(x86)} 'NSIS\makensis.exe' }),
        $(if ($env:ProgramFiles) { Join-Path $env:ProgramFiles 'NSIS\makensis.exe' })
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
    if ($candidates.Count -eq 0) { Stop-WithFailure 'NSIS makensis.exe was not found' }
    $Makensis = $candidates[0]
}

if (-not (Test-Path -LiteralPath $Makensis -PathType Leaf)) {
    Stop-WithFailure "makensis.exe does not exist: $Makensis"
}

$root = Split-Path -Parent $Makensis
$version = (& $Makensis /VERSION 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^v3\.') {
    Stop-WithFailure "Unsupported NSIS version: $version"
}
Write-Ok "NSIS $version"

foreach ($path in @(
    (Join-Path $root 'Contrib\Modern UI 2\MUI2.nsh'),
    (Join-Path $root 'Contrib\Language files\SimpChinese.nlf')
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Stop-WithFailure "Required NSIS file is missing: $path"
    }
}
Write-Ok 'MUI2 and Simplified Chinese language files'

$pluginDir = Join-Path $root 'Plugins\x86-unicode'
foreach ($name in @('System', 'nsDialogs', 'nsExec', 'Math')) {
    $plugin = Join-Path $pluginDir ($name + '.dll')
    if (-not (Test-Path -LiteralPath $plugin -PathType Leaf)) {
        Stop-WithFailure "Required NSIS plugin is missing: $plugin"
    }
}
Write-Ok 'Required Unicode plugins'

Write-Host "NSIS toolchain ready: $root" -ForegroundColor Cyan
