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
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python do ambiente virtual não encontrado: $PythonPath"
}

$PySideDirectory = (& $PythonPath -c "from pathlib import Path; import PySide6; print(Path(PySide6.__file__).resolve().parent)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $PySideDirectory) {
    throw "Não foi possível localizar o PySide6 a partir de $PythonPath"
}
$QmlLint = Join-Path $PySideDirectory "qmllint.exe"
if (-not (Test-Path -LiteralPath $QmlLint -PathType Leaf)) {
    throw "qmllint não encontrado em $PySideDirectory"
}

$QmlFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $RepoRoot "qml") -Recurse -File |
        Where-Object { $_.Extension -in @(".qml", ".js") } |
        Sort-Object FullName |
        Select-Object -ExpandProperty FullName
)
if ($QmlFiles.Count -eq 0) {
    throw "Nenhum arquivo QML/JS encontrado"
}

Push-Location $RepoRoot
try {
    & $QmlLint @QmlFiles
    if ($LASTEXITCODE -ne 0) {
        throw "qmllint encontrou problemas (código $LASTEXITCODE)"
    }
}
finally {
    Pop-Location
}

Write-Host "QML validado: $($QmlFiles.Count) arquivos"
