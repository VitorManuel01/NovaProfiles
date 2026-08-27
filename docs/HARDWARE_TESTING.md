# Checklist de validação física

Registre Windows, versão do NovaProfiles, firmware, revisão do controle, modo de conexão e resultado de cada etapa. Feche o GameSir Connect e use um perfil descartável.

## Conexão e descoberta

- [ ] dongle 2,4 GHz em XInput é detectado;
- [ ] cabo, Bluetooth e dispositivo homônimo não são selecionados por engano;
- [ ] dois controles/coleções resultam em seleção inequívoca ou erro seguro;
- [ ] desconectar durante idle atualiza a UI;
- [ ] reconectar invalida e reaplica o perfil esperado uma única vez;
- [ ] suspensão/retomada do Windows recupera o estado.
- [ ] desconexão/reconexão mais rápida que o intervalo de polling não deixa a UI em falso positivo; se reproduzível, registre o timing e reaplique manualmente;

## Aplicação

- [ ] RB, L4 e R4 padrão são restaurados corretamente;
- [ ] cada destino seguro conhecido funciona no jogo;
- [ ] escrita parcial/simulada é tratada como falha;
- [ ] desconexão em cada etapa da sequência não marca o perfil como ativo;
- [ ] edição do perfil ativo mostra pendência até aplicar;
- [ ] falha não apaga a mensagem específica nem muda o estado aplicado;
- [ ] falha no meio da sequência avisa que o mapeamento pode estar parcial e orienta reconectar/reaplicar;
- [ ] GameSir Connect aberto causa bloqueio/aviso, sem disputa de escrita.

## Auto-switch

- [ ] caminho completo correto ativa o perfil;
- [ ] executável homônimo em outro diretório não ativa o perfil;
- [ ] fechar o jogo restaura o perfil padrão;
- [ ] dois jogos simultâneos geram conflito explícito e não provocam uma troca arbitrária;
- [ ] processo inacessível não bloqueia a interface.

## Serviço legado

- [ ] `running` bloqueia aplicação;
- [ ] `stopped` permite aplicação;
- [ ] acesso negado, timeout, serviço ausente e erro inesperado exibem estados corretos;
- [ ] `unknown` bloqueia gravação;
- [ ] `PARAR_SERVICO_NSSM_ANTIGO.cmd` propaga sucesso e falha.

## Layout e longa duração

- [ ] testar US e ABNT2, especialmente pontuação e teclas ISO;
- [ ] testar escala 100%, 125%, 150% e 200%;
- [ ] testar resolução mínima e teclado sem mouse;
- [ ] executar ciclos de troca/reconexão por pelo menos 30 minutos;
- [ ] confirmar ausência de crescimento contínuo de threads, handles e memória.

Não publique captura USB bruta antes de verificar serial, caminho de instância e outros identificadores.
