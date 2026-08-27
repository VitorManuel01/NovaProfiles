# Contribuindo com o NovaProfiles

Obrigado pelo interesse. Mudanças pequenas, testáveis e apoiadas por evidência de hardware são mais fáceis de revisar.

## Preparação

1. Use Windows x64 e CPython 3.11 a 3.14 x64.
2. Execute `INSTALAR.cmd` para runtime ou `packaging\install.ps1 -BuildTools` para build.
3. Crie uma branch curta e não inclua `.venv`, `build`, `dist`, perfis pessoais ou logs.
4. Consulte [docs/BUILDING.md](docs/BUILDING.md).

## Antes do pull request

Execute:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -File packaging\lint_qml.ps1
BUILD_EXE.cmd -SkipDependencyInstall
```

Para mudanças HID, execute também [docs/HARDWARE_TESTING.md](docs/HARDWARE_TESTING.md) e informe firmware, conexão e resultados. Capturas de USB podem conter identificadores; sanitize antes de anexar.

## Regras de mudança

- Preserve a regra de segurança: nunca grave quando o serviço legado estiver `running` ou `unknown`.
- Não amplie VID/PID, coleções ou comandos HID com base apenas em suposição.
- Mantenha persistência copy-on-write e importação validada antes da substituição.
- Atualize testes quando corrigir um bug ou alterar um formato.
- Strings visíveis devem usar tradução e manter inglês/pt-BR sincronizados.
- Atualize `CHANGELOG.md` para mudanças voltadas ao usuário.
- Não altere versões em vários arquivos; edite somente `version.py`.
- Não adicione certificado, chave, token ou perfil pessoal ao repositório.

## Pull requests

Explique problema, solução, risco e validação. Mantenha refactors independentes de mudanças de protocolo quando possível. A CI precisa concluir testes, `qmllint` e build.

O projeto ainda não possui uma licença própria escolhida. Contribua apenas se você compreende essa situação; a decisão de licença cabe ao mantenedor e deverá ser formalizada em um arquivo `LICENSE` antes de uma política definitiva de redistribuição.
