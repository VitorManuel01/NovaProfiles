[CmdletBinding()]
param(
    [string]$DistDirectory = "",
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DistDirectory) {
    $DistDirectory = Join-Path $RepoRoot "dist\NovaProfiles"
}
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $RepoRoot "artifacts"
}
$DistDirectory = [System.IO.Path]::GetFullPath($DistDirectory)
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$RepoPrefix = $RepoRoot.TrimEnd('\') + '\'

foreach ($Path in @($DistDirectory, $OutputDirectory)) {
    if (-not $Path.StartsWith($RepoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Caminho de saída fora do repositório: $Path"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $DistDirectory "NovaProfiles.exe") -PathType Leaf)) {
    throw "Build portátil ausente: $DistDirectory"
}

$PythonPath = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Version = (& $PythonPath (Join-Path $PSScriptRoot "generate_version_info.py") --print-version).Trim()
if ($LASTEXITCODE -ne 0 -or -not $Version) {
    throw "Não foi possível ler version.py"
}

foreach ($Document in @(
    "README.md",
    "README.en.md",
    "CHANGELOG.md",
    "CHANGELOG.en.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.en.md",
    "LICENSE",
    "PARAR_SERVICO_NSSM_ANTIGO.cmd",
    "SECURITY.md",
    "SECURITY.en.md",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_NOTICES.en.md"
)) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot $Document) -Destination $DistDirectory -Force
}

$DistPrefix = $DistDirectory.TrimEnd('\') + '\'
foreach ($DirectoryName in @("assets", "docs")) {
    $SourceDirectory = Join-Path $RepoRoot $DirectoryName
    $DestinationDirectory = [System.IO.Path]::GetFullPath(
        (Join-Path $DistDirectory $DirectoryName)
    )
    if (-not $DestinationDirectory.StartsWith(
        $DistPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Destino de documentação inválido: $DestinationDirectory"
    }
    if (Test-Path -LiteralPath $DestinationDirectory) {
        Remove-Item -LiteralPath $DestinationDirectory -Recurse -Force
    }
    Copy-Item -LiteralPath $SourceDirectory -Destination $DestinationDirectory -Recurse
}

$PortableToolDirectory = Join-Path $DistDirectory "packaging"
New-Item -ItemType Directory -Path $PortableToolDirectory -Force | Out-Null
Copy-Item `
    -LiteralPath (Join-Path $RepoRoot "packaging\stop_legacy_service.ps1") `
    -Destination $PortableToolDirectory `
    -Force

$LicenseDirectory = Join-Path $DistDirectory "THIRD_PARTY_LICENSES"
if (Test-Path -LiteralPath $LicenseDirectory) {
    Remove-Item -LiteralPath $LicenseDirectory -Recurse -Force
}
& $PythonPath (Join-Path $PSScriptRoot "collect_licenses.py") `
    --lock (Join-Path $RepoRoot "requirements-build-lock-win-x64.txt") `
    --output $LicenseDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao coletar licenças de terceiros (código $LASTEXITCODE)"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$BaseName = "NovaProfiles-$Version-win-x64"
$Sbom = Join-Path $OutputDirectory "$BaseName.cdx.json"
$Archive = Join-Path $OutputDirectory "$BaseName.zip"
$Checksum = Join-Path $OutputDirectory "$BaseName.sha256"

& $PythonPath (Join-Path $PSScriptRoot "generate_sbom.py") --output $Sbom
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar SBOM (código $LASTEXITCODE)"
}

foreach ($GeneratedPath in @($Archive, $Checksum)) {
    if (Test-Path -LiteralPath $GeneratedPath) {
        Remove-Item -LiteralPath $GeneratedPath -Force
    }
}
Compress-Archive -LiteralPath $DistDirectory -DestinationPath $Archive -CompressionLevel Optimal
$Digest = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $Checksum -Value "$Digest *$([System.IO.Path]::GetFileName($Archive))" -Encoding ascii

& $PythonPath (Join-Path $PSScriptRoot "verify_release.py") `
    --archive $Archive `
    --checksum $Checksum `
    --sbom $Sbom
if ($LASTEXITCODE -ne 0) {
    throw "Verificação do pacote de release falhou (código $LASTEXITCODE)"
}

Write-Host "Pacote: $Archive"
Write-Host "SHA-256: $Checksum"
Write-Host "SBOM: $Sbom"
