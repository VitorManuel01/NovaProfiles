# Arquitetura e invariantes

<p align="center"><strong>Português</strong> | <a href="ARCHITECTURE.en.md">English</a></p>

## Componentes

- `main.py`: ciclo de vida Qt, instância única, tradução e tratamento de falha fatal;
- `qml/`: apresentação e acessibilidade;
- `backend/app_controller.py`: estado público, matching de processos e coordenação assíncrona;
- `backend/profile_store.py`: schema, validação, migração e persistência atômica;
- `backend/hid_controller.py`: descoberta da coleção e protocolo GameSir;
- `backend/startup.py`: entrada de inicialização do usuário;
- `version.py`: única fonte de versão;
- `packaging/`: instalação, VersionInfo, build, smoke, SBOM e pacote de release.

## Fluxo de aplicação

1. A UI ou o detector solicita um perfil por ID e estado persistido.
2. O controlador registra a intenção e serializa a operação fora da thread da UI.
3. O worker confirma que há conexão e que o serviço legado está parado.
4. O adaptador HID seleciona exatamente uma coleção compatível e envia relatórios completos.
5. Somente o sucesso de toda a sequência atualiza o estado aplicado.
6. A UI compara perfil, hash efetivo dos mapeamentos, identidade e geração da conexão para mostrar **Active** ou **Pending**. Alterações apenas de nome/executável não fingem que o hardware mudou.

## Invariantes de segurança

- `unknown` não equivale a serviço parado;
- escrita parcial nunca é sucesso;
- reconexão invalida o estado aplicado anterior;
- alterações em memória só se tornam visíveis após persistência bem-sucedida;
- importação é validada e confirmada antes de substituir dados;
- caminho completo configurado tem precedência sobre nome de executável;
- apenas um worker escreve no HID;
- erros detalhados permanecem disponíveis para UI e log sem expor dados desnecessários.

## Limites atuais

O protocolo é específico ao Super Nova e aos relatórios conhecidos. Suporte futuro a outros dispositivos deve entrar por um `ControllerAdapter` com capabilities explícitas, sem ampliar silenciosamente os destinos considerados seguros.

O protocolo conhecido não oferece ACK/readback usado pelo aplicativo. Por
isso, sucesso significa que o driver aceitou todos os relatórios completos,
não uma confirmação do firmware. Uma desconexão muito breve, ocorrida inteira
entre dois polls e reutilizando o mesmo caminho HID, também pode não ser
observada. Após comportamento físico inesperado, reconecte e reaplique o perfil.

As chamadas de escrita do `hidapi` não expõem cancelamento/timeout portátil no
Windows. O worker único evita concorrência, mas um driver travado ainda pode
atrasar o encerramento. Isolar a escrita em processo cancelável exigirá nova
validação física do protocolo e permanece uma limitação conhecida.
