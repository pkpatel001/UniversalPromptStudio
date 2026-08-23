[CmdletBinding()]
param(
    [switch]$Overwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
$cargo = Get-Command "cargo" -ErrorAction SilentlyContinue
$cargoCommand = if ($null -ne $cargo) { $cargo.Source } else { $null }
if (-not $cargoCommand -and $env:OS -eq "Windows_NT") {
    $cargoCommand = Join-Path $env:USERPROFILE ".cargo/bin/cargo.exe"
}
if (-not $cargoCommand -or -not (Test-Path -LiteralPath $cargoCommand)) {
    throw "cargo is required for desktop packaging."
}

Push-Location $projectRoot
try {
    Invoke-Checked "python" @("-m", "pytest", "-q")
    Invoke-Checked "python" @(
        "-m", "mypy", "Engineering/ReleaseSystem", "Engineering/cli/commands/release.py"
    )
    Invoke-Checked "python" @(
        "-m", "ruff", "check", "--no-fix", "--ignore", "N999",
        "Engineering/ReleaseSystem", "Engineering/Tests/test_release_system.py",
        "Engineering/Tests/test_release_automation.py", "Engineering/cli/commands/release.py"
    )
    Invoke-Checked $cargoCommand @(
        "fmt", "--manifest-path", "Frontend/src-tauri/Cargo.toml", "--", "--check"
    )
    Invoke-Checked $cargoCommand @(
        "clippy", "--locked", "--manifest-path", "Frontend/src-tauri/Cargo.toml",
        "--", "-D", "warnings"
    )
    Invoke-Checked "python" @(
        "-m", "Engineering", "theme", "sync-frontend", "--root", "Themes", "--check"
    )
    Invoke-Checked "npm" @("test", "--prefix", "Frontend")
    Invoke-Checked "npm" @(
        "audit", "--prefix", "Frontend", "--audit-level=low", "--cache", ".cache/npm"
    )
    Invoke-Checked "python" @("-m", "Engineering", "build", "run", "--profile", "full")

    $releaseArguments = @("-m", "Engineering", "release", "run")
    if ($Overwrite) {
        $releaseArguments += "--overwrite"
    }
    Invoke-Checked "python" $releaseArguments
    Invoke-Checked "python" @("-m", "Engineering", "release", "verify")
}
finally {
    Pop-Location
}
