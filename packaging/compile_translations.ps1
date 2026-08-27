[CmdletBinding()]
param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $PythonPath) {
    $PythonPath = Join-Path $RepoRoot ".venv\Scripts\python.exe"
}
$PythonPath = [System.IO.Path]::GetFullPath($PythonPath)
$Translations = Join-Path $RepoRoot "translations"

# The console launchers installed in Scripts can fail with
# PySide6-Essentials because they look for Qt tools on PATH. Resolve the real
# executable from the imported package instead.
$PySideDirectory = (& $PythonPath -c "from pathlib import Path; import PySide6; print(Path(PySide6.__file__).resolve().parent)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $PySideDirectory) {
    throw "Não foi possível localizar o PySide6 a partir de $PythonPath"
}
$LRelease = Join-Path $PySideDirectory "lrelease.exe"

if (-not (Test-Path -LiteralPath $LRelease -PathType Leaf)) {
    throw "lrelease não encontrado em $PySideDirectory"
}
if (-not (Test-Path -LiteralPath $Translations -PathType Container)) {
    throw "Pasta de traduções ausente: $Translations"
}

$Catalogs = @(Get-ChildItem -LiteralPath $Translations -Filter "*.ts" -File | Sort-Object Name)
if ($Catalogs.Count -eq 0) {
    throw "Nenhum catálogo .ts encontrado em $Translations"
}

foreach ($Catalog in $Catalogs) {
    $Output = [System.IO.Path]::ChangeExtension($Catalog.FullName, ".qm")
    & $LRelease $Catalog.FullName -qm $Output
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao compilar $($Catalog.Name) (código $LASTEXITCODE)"
    }
}

Write-Host "Traduções compiladas: $($Catalogs.Count)"
