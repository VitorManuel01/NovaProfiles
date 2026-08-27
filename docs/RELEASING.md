# Processo de release

<p align="center"><strong>Português</strong> | <a href="RELEASING.en.md">English</a></p>

O workflow publica apenas tags `v<SemVer>` e não inventa nem exige um certificado de assinatura.

## Preparação

1. Decida e atualize somente `version.py`.
2. Mova as notas relevantes de **Unreleased** em `CHANGELOG.md`.
3. Atualize locks em uma branch e revise cada mudança de dependência.
4. Execute testes, `qmllint`, build e o checklist físico.
5. Confirme que o portátil não contém perfis, logs, caminhos pessoais ou Qt WebEngine.
6. Confirme os avisos/licenças de terceiros.
7. Confirme que o arquivo `LICENSE` MIT e os avisos de copyright estão presentes no pacote.

## Publicação

Crie uma tag anotada que corresponda exatamente à versão:

```powershell
git tag -a v1.2.0 -m "NovaProfiles 1.2.0"
git push origin v1.2.0
```

A automação valida tag versus `version.py`, instala locks exatos, compila traduções, testa, faz build e cria:

- `NovaProfiles-<versão>-win-x64.zip`;
- `NovaProfiles-<versão>-win-x64.sha256`;
- `NovaProfiles-<versão>-win-x64.cdx.json`.

O job de release usa permissão de escrita somente depois do build, verifica que a tag existe e publica esses três arquivos. Não há chave ou certificado no workflow.

## Assinatura futura

Caso o autor adquira um certificado real, a assinatura deve ser adicionada em etapa isolada, com segredo protegido por Environment, aprovação e documentação do emissor/timestamp. Nunca use certificado de teste para aparentar confiança pública e nunca armazene PFX ou senha no repositório.
