# Política de segurança

<p align="center"><strong>Português</strong> | <a href="SECURITY.en.md">English</a></p>

## Versões suportadas

Somente a versão mais recente publicada recebe correções de segurança. Builds locais e versões anteriores podem ajudar no diagnóstico, mas não recebem backports garantidos.

## Como relatar

Não publique detalhes de uma vulnerabilidade explorável em uma issue comum. Use **Report a vulnerability** na aba Security do repositório, que cria um [GitHub Security Advisory privado](https://github.com/VitorManuel01/NovaProfiles/security/advisories/new).

Inclua, quando possível:

- versão/commit e edição do Windows;
- impacto e pré-condições;
- passos mínimos para reproduzir;
- arquivos, relatórios HID ou logs estritamente necessários;
- uma sugestão de correção, se houver.

Remova tokens, nomes de usuário, caminhos pessoais e dados de jogos. Não teste em dispositivos ou computadores de terceiros sem autorização. O mantenedor confirmará o recebimento pelo próprio advisory e coordenará correção e divulgação ali; nenhum prazo fixo é prometido.

## Escopo sensível

São especialmente relevantes: seleção incorreta de interface HID, escrita parcial ou concorrente, importação de perfil malformado, execução automática no login, manipulação insegura de caminhos, carga de QML/arquivos não confiáveis e exposição de dados em logs.

O NovaProfiles não deve solicitar privilégios administrativos para uso normal. O script que para o serviço NSSM antigo é uma ação separada e explicitamente elevada.
