[CmdletBinding()]
param(
    [switch]$BuildTools
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Host "Criando ambiente virtual..."
        if (Get-Command py.exe -ErrorAction SilentlyContinue) {
            & py.exe -3 -m venv .venv
        }
        elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
            & python.exe -m venv .venv
        }
        else {
            throw "Python não encontrado. Instale CPython 3.11 a 3.14 x64."
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível criar .venv (código $LASTEXITCODE)"
        }
    }

    & $VenvPython packaging\check_environment.py
    if ($LASTEXITCODE -ne 0) {
        throw "Ambiente Python incompatível"
    }

    Write-Host "Instalando versão fixada do pip..."
    & $VenvPython -m pip install --disable-pip-version-check --no-deps --only-binary=:all: -r requirements-bootstrap-lock.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Falha no bootstrap do pip (código $LASTEXITCODE)"
    }

    # Remove the old meta/Addons distributions before reinstalling Essentials.
    # Otherwise a reused .venv can leak WebEngine and other unused Qt modules
    # into an otherwise pinned build.
    & $VenvPython -m pip uninstall --yes PySide6 PySide6-Addons
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao remover pacotes Qt incompatíveis (código $LASTEXITCODE)"
    }

    $Lock = if ($BuildTools) {
        "requirements-build-lock-win-x64.txt"
    }
    else {
        "requirements-lock-win-x64.txt"
    }
    Write-Host "Instalando dependências exatas de $Lock..."
    & $VenvPython -m pip install --disable-pip-version-check --force-reinstall --no-deps --only-binary=:all: -r $Lock
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar o lock (código $LASTEXITCODE)"
    }

    & $VenvPython -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Dependências inconsistentes (código $LASTEXITCODE)"
    }

    & $VenvPython packaging\verify_dependencies.py --lock $Lock
    if ($LASTEXITCODE -ne 0) {
        throw "O ambiente não corresponde ao lock (código $LASTEXITCODE)"
    }

    & (Join-Path $PSScriptRoot "compile_translations.ps1") -PythonPath $VenvPython
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao compilar traduções (código $LASTEXITCODE)"
    }
}
finally {
    Pop-Location
}

Write-Host "Instalação concluída."
