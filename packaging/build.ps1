[CmdletBinding()]
param(
    [switch]$SkipDependencyInstall,
    [switch]$SkipArchive,
    [string]$VersionInfo = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not $VersionInfo) {
    $VersionInfo = Join-Path $RepoRoot "build\version_info.txt"
}
$VersionInfo = [System.IO.Path]::GetFullPath($VersionInfo)
$BuildRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot "build"))
$BuildPrefix = $BuildRoot.TrimEnd('\') + '\'
if (-not $VersionInfo.StartsWith($BuildPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "VersionInfo deve ficar dentro de build\: $VersionInfo"
}

Push-Location $RepoRoot
try {
    if (-not $SkipDependencyInstall) {
        & (Join-Path $PSScriptRoot "install.ps1") -BuildTools
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao preparar dependências (código $LASTEXITCODE)"
        }
    }
    elseif (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        throw ".venv ausente. Execute INSTALAR.cmd ou remova -SkipDependencyInstall."
    }

    & $PythonPath packaging\verify_dependencies.py --lock requirements-build-lock-win-x64.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Ambiente de build contaminado ou fora do lock (código $LASTEXITCODE)"
    }

    & (Join-Path $PSScriptRoot "compile_translations.ps1") -PythonPath $PythonPath
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao compilar traduções (código $LASTEXITCODE)"
    }

    & $PythonPath packaging\generate_version_info.py --output $VersionInfo
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar VersionInfo (código $LASTEXITCODE)"
    }

    $PreviousVersionInfo = $env:NOVAPROFILES_VERSION_INFO
    $PreviousPath = $env:PATH
    $BasePython = (& $PythonPath -c "import sys; print(sys.base_prefix)").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $BasePython) {
        throw "Não foi possível localizar o Python base"
    }
    $CleanPath = @(
        (Split-Path $PythonPath -Parent),
        $BasePython,
        (Join-Path $BasePython "DLLs"),
        (Join-Path $env:SystemRoot "System32"),
        $env:SystemRoot
    ) | Select-Object -Unique
    try {
        $env:NOVAPROFILES_VERSION_INFO = $VersionInfo
        # Dependency discovery must not capture unrelated DLLs from developer
        # tools (for example Poppler ICU/OpenSSL) present on the caller's PATH.
        $env:PATH = $CleanPath -join [System.IO.Path]::PathSeparator
        & $PythonPath -m PyInstaller --noconfirm --clean --distpath dist --workpath build NovaProfiles.spec
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller falhou (código $LASTEXITCODE)"
        }
    }
    finally {
        $env:NOVAPROFILES_VERSION_INFO = $PreviousVersionInfo
        $env:PATH = $PreviousPath
    }

    & $PythonPath packaging\verify_artifact.py dist\NovaProfiles
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke do artefato falhou (código $LASTEXITCODE)"
    }

    if (-not $SkipArchive) {
        & (Join-Path $PSScriptRoot "package_release.ps1")
        if ($LASTEXITCODE -ne 0) {
            throw "Empacotamento falhou (código $LASTEXITCODE)"
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Build concluído: $RepoRoot\dist\NovaProfiles\NovaProfiles.exe"
