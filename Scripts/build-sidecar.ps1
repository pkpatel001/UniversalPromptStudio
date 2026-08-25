[CmdletBinding()]
param(
    [string]$TargetTriple = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try {
        $hash = $algorithm.ComputeHash($stream)
        return -join ($hash | ForEach-Object { $_.ToString("x2") })
    }
    finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $Arguments"
    }
}

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$lockPath = Join-Path $PSScriptRoot "sidecar-requirements.lock"
$entrypoint = Join-Path $PSScriptRoot "ups_sidecar.py"
$cacheRoot = Join-Path $projectRoot ".cache/sidecar-build"
$binaryRoot = Join-Path $projectRoot "Frontend/src-tauri/binaries"
$binaryName = "universal-prompt-studio-backend"

if (-not $TargetTriple) {
    $TargetTriple = (& rustc --print host-tuple).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $TargetTriple) {
        throw "rustc --print host-tuple is required to name the sidecar."
    }
}
if ($TargetTriple -notmatch '^[a-z0-9_]+-[a-z0-9_]+-[a-z0-9_]+(?:-[a-z0-9_]+)?$') {
    throw "Target triple is invalid: $TargetTriple"
}
if ($TargetTriple -notmatch 'windows') {
    throw "A-001.2 currently builds only the Windows sidecar."
}

$lockHash = Get-Sha256 $lockPath
$environmentRoot = Join-Path $cacheRoot ("venv-" + $lockHash.Substring(0, 16))
$environmentPython = Join-Path $environmentRoot "Scripts/python.exe"
$wheelCache = Join-Path $projectRoot ".cache/sidecar-lock-wheels"
$workRoot = Join-Path $cacheRoot $TargetTriple
$distRoot = Join-Path $workRoot "dist"
$pyinstallerWork = Join-Path $workRoot "work"
$specRoot = Join-Path $workRoot "spec"

New-Item -ItemType Directory -Path $cacheRoot, $binaryRoot, $workRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $environmentPython -PathType Leaf)) {
    Invoke-Checked "python" @("-m", "venv", $environmentRoot)
}

$installArguments = @(
    "-m", "pip", "install", "--disable-pip-version-check", "--require-hashes",
    "--only-binary=:all:", "--requirement", $lockPath
)
if (Test-Path -LiteralPath $wheelCache -PathType Container) {
    $installArguments += @("--find-links", $wheelCache)
}
Invoke-Checked $environmentPython $installArguments

$previousHashSeed = $env:PYTHONHASHSEED
$previousSourceDate = $env:SOURCE_DATE_EPOCH
try {
    $env:PYTHONHASHSEED = "0"
    $env:SOURCE_DATE_EPOCH = "0"
    Invoke-Checked $environmentPython @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", $binaryName, "--paths", $projectRoot, "--distpath", $distRoot,
        "--workpath", $pyinstallerWork, "--specpath", $specRoot, $entrypoint
    )
}
finally {
    $env:PYTHONHASHSEED = $previousHashSeed
    $env:SOURCE_DATE_EPOCH = $previousSourceDate
}

$builtBinary = Join-Path $distRoot ($binaryName + ".exe")
$targetBinary = Join-Path $binaryRoot ($binaryName + "-" + $TargetTriple + ".exe")
if (-not (Test-Path -LiteralPath $builtBinary -PathType Leaf)) {
    throw "PyInstaller did not produce the expected sidecar executable."
}
Copy-Item -LiteralPath $builtBinary -Destination $targetBinary -Force

$identityText = (& $targetBinary --identity | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "The built sidecar identity probe failed."
}
$identity = $identityText | ConvertFrom-Json
if (
    $identity.sidecar_identity -ne "com.universalpromptstudio.backend" -or
    $identity.application_version -ne "0.2.0-alpha" -or
    $identity.protocol_version -ne 1
) {
    throw "The built sidecar identity does not match the application contract."
}

$binaryHash = Get-Sha256 $targetBinary
$manifestPath = Join-Path $binaryRoot ($binaryName + "-" + $TargetTriple + ".manifest.json")
$manifest = [ordered]@{
    schema_version = 1
    sidecar_identity = $identity.sidecar_identity
    application_version = $identity.application_version
    protocol_version = $identity.protocol_version
    target_triple = $TargetTriple
    builder = [ordered]@{
        python = (& python --version 2>&1 | Out-String).Trim().Replace("Python ", "")
        pyinstaller = "6.22.2"
        lock_sha256 = $lockHash
    }
    artifact = [ordered]@{
        file_name = [IO.Path]::GetFileName($targetBinary)
        size = (Get-Item -LiteralPath $targetBinary).Length
        sha256 = $binaryHash
    }
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Output "Sidecar built: $targetBinary"
Write-Output "Sidecar manifest: $manifestPath"
Write-Output "Sidecar SHA256: $binaryHash"
