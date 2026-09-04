[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $FilePath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{40}$')]
    [string] $CertificateThumbprint,

    [string] $TimestampServer = 'http://timestamp.digicert.com'
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -Force

$candidateFile = $FilePath

if (-not (Test-Path -LiteralPath $candidateFile)) {
    $tauriRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\Frontend\src-tauri')).Path
    $candidateFile = Join-Path $tauriRoot $FilePath
}

$resolvedFile = (Resolve-Path -LiteralPath $candidateFile).Path
$normalizedThumbprint = $CertificateThumbprint.Replace(' ', '').ToUpperInvariant()
$certificateStore = [System.Security.Cryptography.X509Certificates.X509Store]::new('My', 'CurrentUser')
$certificateStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
$certificate = $certificateStore.Certificates.Find(
    [System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint,
    $normalizedThumbprint,
    $false
) | Where-Object { $_.HasPrivateKey } | Select-Object -First 1

if ($null -eq $certificate) {
    $certificateStore.Close()
    throw "The Windows signing certificate $normalizedThumbprint is not installed in the current-user Personal store with an accessible private key."
}
$now = Get-Date
$codeSigningOid = '1.3.6.1.5.5.7.3.3'
$hasCodeSigningUsage = $null -ne ($certificate.EnhancedKeyUsageList | Where-Object {
        $_.ObjectId -eq $codeSigningOid
    })

if (-not $certificate.HasPrivateKey) {
    throw "The Windows signing certificate $normalizedThumbprint does not have an accessible private key."
}

if ($now -lt $certificate.NotBefore -or $now -gt $certificate.NotAfter) {
    throw "The Windows signing certificate $normalizedThumbprint is not currently valid."
}

if (-not $hasCodeSigningUsage) {
    throw "The Windows signing certificate $normalizedThumbprint is not valid for Code Signing."
}

$signature = Set-AuthenticodeSignature `
    -FilePath $resolvedFile `
    -Certificate $certificate `
    -HashAlgorithm SHA256 `
    -TimestampServer $TimestampServer

$certificateStore.Close()

if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Signing failed for $resolvedFile`: $($signature.StatusMessage)"
}

if ($null -eq $signature.TimeStamperCertificate) {
    throw "Signing succeeded for $resolvedFile, but no timestamp was applied."
}

if ([System.IO.Path]::GetFileName($resolvedFile) -like 'universal-prompt-studio-backend-*.exe') {
    $manifestPath = [System.IO.Path]::ChangeExtension($resolvedFile, '.manifest.json')

    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "The signed sidecar manifest was not found: $manifestPath"
    }

    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($null -eq $manifest.artifact) {
        throw "The signed sidecar manifest does not contain an artifact record: $manifestPath"
    }

    $manifest.artifact.size = (Get-Item -LiteralPath $resolvedFile).Length
    $manifest.artifact.sha256 = (Get-FileHash -LiteralPath $resolvedFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifestJson = $manifest | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText(
        $manifestPath,
        $manifestJson + [Environment]::NewLine,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Output "Successfully signed and timestamped: $resolvedFile"
