# Changelog

Todas as mudanças relevantes do NovaProfiles são documentadas aqui. O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [1.2.0] - 2026-08-27

### Adicionado

- estado aplicado baseado em revisão do perfil e geração da conexão;
- indicação de alterações pendentes e reaplicação segura após reconexão;
- fila de trabalho para operações HID/serviço sem bloquear a interface;
- validação transacional de perfis, prévia de importação e backups;
- correspondência de jogos por caminho completo quando configurado;
- interface responsiva, acessível e traduzida para pt-BR;
- testes automatizados de persistência, protocolo, matching e reconexão;
- CI Windows com testes, `qmllint` e build portátil;
- artefatos de release com VersionInfo, checksum SHA-256 e SBOM CycloneDX;
- licença de terceiros coletada no portátil e smoke QML seguro no executável;
- instância única no Windows, com reabertura da janela já em execução;
- documentação de build, release, segurança e validação física.

### Alterado

- dependência Qt reduzida de `PySide6` para `PySide6-Essentials`;
- estado do serviço legado agora é explícito (`running`, `stopped` ou `unknown`) e falha de consulta bloqueia gravações;
- escrita HID exige relatório completo e oferece erros específicos;
- scripts `.cmd` preservam códigos de saída;
- build usa locks exatos, não atualiza `pip` livremente e desativa UPX;
- build isola o `PATH` e remove estilos/módulos QML não utilizados;
- consulta ao serviço legado usa a API numérica do Windows, independente do idioma;
- perfis corrompidos são preservados antes da recuperação e esquemas futuros não são sobrescritos;
- versão passou a ter uma única fonte em `version.py`.

### Segurança

- gravações concorrentes com o serviço NSSM antigo são bloqueadas quando não é possível provar que ele está parado;
- importações deixam de substituir dados antes de validação e confirmação.

## [1.1.0] - 2026-08-26

### Adicionado

- primeira versão pública da interface QML, perfis automáticos e gravação HID para o GameSir Super Nova.

[Unreleased]: https://github.com/VitorManuel01/NovaProfiles/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/VitorManuel01/NovaProfiles/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/VitorManuel01/NovaProfiles/releases/tag/v1.1.0
