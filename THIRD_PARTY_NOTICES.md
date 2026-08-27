# Avisos de software de terceiros

O NovaProfiles depende de componentes mantidos por terceiros. Este resumo é informativo; os textos incluídos nos pacotes e os repositórios de origem são a referência legal. Um release deve preservar os arquivos de licença coletados pelo PyInstaller e incluir este documento e o SBOM CycloneDX.

O pacote portátil inclui `THIRD_PARTY_LICENSES`: os textos declarados pelos
wheels de runtime e build são coletados automaticamente (inclusive a licença e
exceção do bootloader PyInstaller), e as licenças GPL/LGPL/Qt
compartilhadas mantidas em `licenses/` são incluídas integralmente. Os textos
padronizados desse diretório vêm da lista de licenças SPDX; os avisos
específicos de cada componente continuam prevalecendo.

## Runtime

| Componente | Uso | Licença declarada pelo projeto |
|---|---|---|
| [PySide6-Essentials / Qt for Python](https://pypi.org/project/PySide6-Essentials/) | Qt Core, GUI, Widgets, QML, Quick e Quick Controls | LGPL-3.0-only ou GPL-2.0-only ou GPL-3.0-only; licença comercial também disponível |
| [shiboken6](https://pypi.org/project/shiboken6/) | suporte às bindings Qt | LGPL-3.0-only ou GPL-2.0-only ou GPL-3.0-only; licença comercial também disponível |
| [hidapi (cython-hidapi)](https://pypi.org/project/hidapi/) | acesso HID no Windows | opções descritas no `LICENSE.txt` do projeto, incluindo BSD/GPL |
| [psutil](https://github.com/giampaolo/psutil) | enumeração de processos | BSD-3-Clause |

O pacote Essentials foi escolhido porque o aplicativo não usa Qt WebEngine. Assim, o build curado não deve distribuir Chromium/Qt WebEngine. O smoke de artefato falha se encontrar esses módulos.

## Ferramentas de build

Estas ferramentas são usadas para produzir o executável e podem não ser bibliotecas importadas em runtime. Seus textos também são preservados porque o executável incorpora o bootloader do PyInstaller:

| Componente | Licença/projeto |
|---|---|
| [PyInstaller](https://pyinstaller.org/en/stable/license.html) | GPL-2.0-or-later com exceção para distribuição de aplicações empacotadas |
| [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | consulte a licença do pacote/repositório |
| [altgraph](https://github.com/ronaldoussoren/altgraph) | MIT |
| [packaging](https://github.com/pypa/packaging) | Apache-2.0 ou BSD-2-Clause |
| [pefile](https://github.com/erocarrera/pefile) | MIT |
| [pywin32-ctypes](https://github.com/enthought/pywin32-ctypes) | BSD-3-Clause |
| [setuptools](https://github.com/pypa/setuptools) | MIT |

As versões exatas estão em `requirements-lock-win-x64.txt`, `requirements-build-lock-win-x64.txt` e no SBOM de cada release.

## Código do NovaProfiles

Ainda não existe um `LICENSE` escolhido para o código próprio do NovaProfiles. Este documento não concede uma licença para ele e não substitui a decisão do autor.
