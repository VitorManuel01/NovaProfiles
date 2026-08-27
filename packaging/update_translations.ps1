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

$PySideDirectory = (& $PythonPath -c "from pathlib import Path; import PySide6; print(Path(PySide6.__file__).resolve().parent)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $PySideDirectory) {
    throw "Não foi possível localizar o PySide6 a partir de $PythonPath"
}
$LUpdate = Join-Path $PySideDirectory "lupdate.exe"
if (-not (Test-Path -LiteralPath $LUpdate -PathType Leaf)) {
    throw "lupdate não encontrado em $PySideDirectory"
}

$Catalog = Join-Path $RepoRoot "translations\novaprofiles_pt_BR.ts"
$BackendMarkers = Join-Path $RepoRoot "build\backend_translation_strings.h"
& $PythonPath (Join-Path $RepoRoot "packaging\generate_translation_sources.py") --output $BackendMarkers
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar marcadores das strings Python"
}

& $LUpdate -no-obsolete (Join-Path $RepoRoot "qml") $BackendMarkers -ts $Catalog
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao atualizar $Catalog (código $LASTEXITCODE)"
}

Write-Host "Catálogo QML/Python atualizado. Traduza entradas novas antes de compilar."
