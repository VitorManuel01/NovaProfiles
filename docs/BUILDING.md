# Build e dependências

<p align="center"><strong>Português</strong> | <a href="BUILDING.en.md">English</a></p>

## Ambiente suportado

- Windows 10/11 x64;
- CPython 3.11, 3.12, 3.13 ou 3.14 x64;
- PowerShell 5.1 ou superior;
- acesso ao PyPI para a primeira instalação.

O build é intencionalmente Windows-only porque o artefato inclui wheels e binários Qt/HID dessa plataforma.

## Arquivos de dependência

- `requirements.txt`: faixas aceitas para manutenção;
- `requirements-build.txt`: faixas aceitas de build;
- `requirements-lock-win-x64.txt`: runtime exato;
- `requirements-build-lock-win-x64.txt`: runtime + build exatos;
- `requirements-bootstrap-lock.txt`: versão exata do `pip` usada no bootstrap.

Os scripts instalam apenas wheels (`--only-binary=:all:`) e desativam resolução transitiva (`--no-deps`), pois todas as dependências estão enumeradas no lock. Depois executam `pip check`.

Ao reutilizar `.venv`, o instalador remove explicitamente os antigos pacotes
`PySide6`/`PySide6-Addons`, reinstala os pins e verifica versões e ausência
desses extras antes de permitir um build. Isso evita que WebEngine ou outros
módulos não usados vazem de um ambiente antigo para o portátil.

Os locks atuais abrangem várias versões do CPython, cujos pacotes nativos possuem wheels diferentes. Eles fixam versões, mas não incluem uma lista parcial de hashes, que daria falsa impressão de cobertura. Para obter verificação criptográfica completa, o mantenedor deve baixar **todas** as wheels Windows x64 aceitas para cada Python suportado em uma máquina de release, validar a origem, gerar hashes SHA-256 e somente então habilitar `--require-hashes`. Não copie hashes de uma plataforma incompleta.

## Instalar

Runtime:

```powershell
.\INSTALAR.cmd
```

Runtime e ferramentas de build:

```powershell
powershell -NoProfile -File .\packaging\install.ps1 -BuildTools
```

Não use `pip install --upgrade pip` sem versão. O bootstrap instala a versão declarada no lock.

## Build portátil

Modo amigável:

```powershell
.\BUILD_EXE.cmd
```

Modo não interativo, após preparar `.venv`:

```powershell
$env:NOVAPROFILES_NO_PAUSE = "1"
powershell -NoProfile -File .\packaging\build.ps1 -SkipDependencyInstall
```

Para apenas criar `dist\NovaProfiles`, acrescente `-SkipArchive`.

O processo:

1. compila `translations\*.ts` com o `lrelease` fornecido pelo PySide6;
2. gera `build\version_info.txt` a partir de `version.py`;
3. executa o spec rastreado com UPX desativado;
4. remove módulos QML/Addons não usados;
5. valida PE/versão/recursos e carrega a interface do executável em modo offscreen;
6. inclui documentação no portátil;
7. cria ZIP, SHA-256 e SBOM CycloneDX em `artifacts`;
8. testa a integridade do ZIP, seu checksum, conteúdo e versão do SBOM.

Para fornecer outro arquivo VersionInfo gerado dentro do repositório:

```powershell
powershell -NoProfile -File .\packaging\build.ps1 -VersionInfo .\build\custom-version-info.txt
```

O spec recebe esse caminho por `NOVAPROFILES_VERSION_INFO`. O arquivo precisa seguir o formato VersionInfo do PyInstaller.

## Validação local

```powershell
.venv\Scripts\python.exe -m compileall -q main.py version.py backend packaging
.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -File packaging\lint_qml.ps1
.venv\Scripts\python.exe packaging\verify_artifact.py dist\NovaProfiles
```

Ao alterar uma string visível, atualize o catálogo e traduza qualquer entrada
nova antes de recompilar:

```powershell
powershell -NoProfile -File packaging\update_translations.ps1
powershell -NoProfile -File packaging\compile_translations.ps1
```

O smoke do artefato executa somente `--version` e `--smoke-test`. Este último
carrega a interface com os plugins offscreen e Windows, usando um controller nulo: não lê perfis,
não procura processos e não abre nem grava no HID. Além disso, a verificação
confere PE, `FileVersion`, recursos obrigatórios e ausência dos módulos Qt não
utilizados. O checklist físico permanece obrigatório para mudanças de protocolo.
