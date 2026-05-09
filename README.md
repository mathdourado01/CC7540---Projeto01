# CC7540 - Plataforma de Acompanhamento de Estudos com Gamificação

## Links do Trello

StudyRats: https://trello.com/b/1j6WDfBm/studyrats  
Kanban de Riscos: https://trello.com/b/sFC0pKBk/kanban-de-riscos

---

## Objetivo do Projeto

O StudyRats é uma aplicação web voltada ao acompanhamento de estudos, permitindo que usuários registrem sessões de estudo, visualizem métricas de desempenho, acompanhem sua constância e recebam estímulos por meio de gamificação.

A proposta do sistema é apoiar estudantes na organização da rotina acadêmica, incentivando a continuidade dos estudos por meio de recursos como pontuação, níveis, conquistas, streaks e ranking local.

---

## Projeto Ideia

- Aplicação web acessível via navegador
- Execução local
- Cadastro de usuários
- Login de usuários
- Dashboard de métricas
- Registro de sessões de estudo
- Histórico de estudos
- Sistema de pontuação, níveis e conquistas
- Acompanhamento de streaks
- Ranking local entre usuários do mesmo ambiente
- Kanban da Sprint
- Kanban de Riscos

---

## Participantes

- Vinicius Duarte — Product Owner (PO)
- Julian Ryu — Scrum Master
- Matheus Dourado Valle — Equipe de Desenvolvimento
- João Pedro Sabino — Equipe de Desenvolvimento
- João Pedro Peterutto — Equipe de Desenvolvimento

---

## Papéis

### Product Owner (PO)

- Definir a visão do produto
- Elaborar e priorizar o Product Backlog
- Especificar e refinar histórias de usuário
- Definir critérios de aceitação
- Validar entregas nas Sprint Reviews
- Representar o valor de negócio do produto

### Scrum Master (SM)

- Facilitar as cerimônias do Scrum
- Apoiar o time na adoção das práticas ágeis
- Monitorar métricas como velocidade, burndown, lead time, cycle time, throughput e WIP
- Identificar e registrar impedimentos
- Apoiar a melhoria contínua por meio das retrospectivas

### Equipe de Desenvolvimento

- Estimar histórias de usuário
- Implementar as funcionalidades planejadas
- Manter o código versionado e organizado
- Garantir qualidade técnica
- Apoiar o PO e o SM quando necessário

---

# Sprint 1

## Objetivo da Sprint 1

O objetivo da Sprint 1 foi desenvolver a base funcional da plataforma StudyRats, contemplando a implementação das funcionalidades de cadastro, login e dashboard de métricas, de forma a permitir o acesso dos usuários ao sistema e a visualização inicial de informações relevantes sobre seu desempenho.

Além disso, a sprint também contemplou a implementação do registro de sessões de estudo e do ranking local de comparação, ampliando a experiência do usuário com recursos de acompanhamento de progresso e comparação de desempenho dentro da plataforma.

A imagem do quadro Kanban pode ser encontrada na pasta `arquivos_de_aula`.

---

## Entregas da Sprint 1

### Parte 1

Nesta etapa, o projeto iniciou a estrutura principal da aplicação, incluindo a organização inicial das telas, definição do fluxo de navegação e criação da base para autenticação e acompanhamento de estudos.

### Parte 2

Nesta etapa, o projeto adicionou o serviço de registro de sessão, o fluxo de envio do formulário no app, a inserção na tabela `study_sessions` e o uso de `returning="minimal"` para manter o salvamento enxuto.

### Parte 3

Nesta etapa, o projeto passou a carregar disciplinas já utilizadas pelo usuário e atualizou o histórico de estudos imediatamente após o salvamento de uma nova sessão.

### Parte 4

Nesta etapa, o projeto adicionou a aba de ranking do grupo, a listagem de participantes, a ordenação dos participantes, a exibição da posição do usuário no ranking e a paginação da lista.

---

# Sprint 2

## Objetivo da Sprint 2

O objetivo da Sprint 2 foi evoluir o StudyRats com mecanismos de motivação e acompanhamento de constância, priorizando gamificação, feedback imediato e streaks.

A sprint teve como foco principal aumentar o engajamento do usuário, permitindo que ele acompanhe sua evolução por meio de pontos, níveis, conquistas e dias consecutivos de estudo.

---

## Histórias de Usuário da Sprint 2

### HU5 — Sistema de Feedback e Gamificação

Como um usuário que luta contra a procrastinação, eu quero receber feedback imediato através de pontos, níveis e conquistas por metas batidas, para aumentar minha motivação e manter a constância nos estudos sem perder o foco acadêmico.

#### Funcionalidades entregues

- Cálculo de pontos por registro de estudo
- Subida de nível por pontuação acumulada
- Progressão da gamificação do usuário
- Regras de gamificação isoladas do front-end e do banco
- Armazenamento de pontos, níveis e conquistas
- Prevenção de duplicidade no processamento
- Integração da gamificação ao fluxo de salvar sessão
- Verificação e desbloqueio de conquistas
- Componentes visuais para pontos, níveis e conquistas

#### Critérios de aceite validados

- Feedback visual exibido quando o usuário completa um novo registro de estudo
- Nenhum alerta exibido quando o tempo registrado não é suficiente para atingir uma nova meta
- Processamento da gamificação realizado sem duplicidade e em menos de 3 segundos

Status: Concluída

---

### HU6 — Acompanhamento de Sequências / Streaks

Como usuário, eu quero acompanhar meus dias consecutivos de estudo, para manter minha constância e visualizar meu progresso diretamente na tela inicial.

#### Funcionalidades entregues

- Cálculo de incremento da streak
- Manutenção da streak no mesmo dia
- Reset após quebra de sequência
- Função isolada para cálculo
- Componentes visuais para streak atual e maior streak
- Atualização visual imediata
- Leitura rápida na abertura do app
- Rotina de recálculo a partir do histórico
- Simulação em lote para testar sequências

#### Critérios de aceite validados

- Streak incrementada corretamente em dias consecutivos de estudo
- Streak resetada após quebra da sequência
- Informação exibida diretamente na tela inicial, sem exigir navegação extra

Status: Concluída

---

## Kanban da Sprint 2

Durante a Sprint 2, o quadro Kanban foi utilizado para acompanhar a evolução das tarefas entre as colunas de planejamento, desenvolvimento, teste e conclusão.

A Sprint 2 foi encerrada com todas as histórias planejadas concluídas.

Resumo:

- Histórias planejadas: 2
- Histórias concluídas: 2
- Cartões entregues: 40
- Pendências finais: 0

---

## Kanban de Riscos

Durante a Sprint 2, a equipe também utilizou um Kanban de Riscos para acompanhar ameaças ao andamento do projeto.

### Riscos ocorridos

#### RISK-01 — Regras de gamificação e streak mal refinadas

O risco ocorreu quando as regras de pontos, níveis, conquistas e streak precisaram de mais ajustes durante a implementação.

A contingência foi refinar as regras, separar melhor as responsabilidades e validar os comportamentos com testes.

Impacto: retrabalho e atraso pontual, sem comprometer a entrega final.

#### RISK-03 — Recuperação de senha dependente de autenticação/e-mail

O risco ocorreu porque a recuperação de senha dependia de integração com autenticação e envio de e-mail, tornando a entrega mais complexa e incompatível com o escopo do projeto.

A contingência foi priorizar as HUs principais da Sprint 2 e tratar essa dependência sem bloquear gamificação e streak.

Impacto: ajuste de prioridade e maior foco no escopo essencial da sprint.

---

### Riscos mitigados que não ocorreram

#### RISK-02 — Desempenho acima de 3 segundos

Mitigado com testes contínuos e medição de tempo de resposta desde o início.

#### RISK-04 — Baixa disponibilidade da equipe

Mitigado com divisão das tarefas em cartões menores e priorização das funcionalidades mais críticas.

#### RISK-05 — Falha na atualização do streak na tela inicial

Mitigado com atualização do streak na tela inicial e testes recorrentes da funcionalidade.

---

## Indicadores da Sprint 2

A Sprint 2 utilizou indicadores ágeis para monitorar o desempenho do time e a evolução das entregas.

### Burndown

O Burndown mostrou a redução dos cartões restantes ao longo da Sprint.

A Sprint iniciou com 40 cartões planejados e terminou com 0 pendências.

### Lead Time

Lead Time médio: aproximadamente 11,44 dias corridos.

Esse indicador representa o tempo total entre a entrada do cartão no fluxo da Sprint e sua conclusão.

### Cycle Time

Cycle Time médio: aproximadamente 2,52 dias corridos.

Esse indicador representa o tempo entre o início efetivo do desenvolvimento e a conclusão da tarefa.

### Throughput

Throughput da Sprint 2: 2 histórias concluídas e 40 cartões entregues.

Esse indicador representa a quantidade de itens concluídos no período da Sprint.

### Velocidade

Velocidade da Sprint 2: 21 pontos entregues.

Esse indicador representa a quantidade de pontos de história entregues na Sprint.

### WIP

WIP médio: aproximadamente 4,91 cartões.

O WIP representa a quantidade média de tarefas em andamento ao mesmo tempo durante a Sprint.

---

## Retrospectiva Final da Sprint 2

Em relação à Sprint 1, a Sprint 2 mostrou uma melhora clara no controle do trabalho e na resposta aos riscos.

O Kanban continuou ajudando na visualização das tarefas, mas a equipe também conseguiu acompanhar melhor os riscos, dividir as entregas em cartões menores e concluir todos os itens planejados até o fechamento.

O problema de dependência entre tarefas foi resolvido, pois desde o planejamento a equipe pensou nas atividades de forma que os membros pudessem trabalhar em paralelo, tornando o desenvolvimento mais dinâmico e evitando bloqueios entre as entregas.

O principal ponto negativo foi a disponibilidade dos membros, já que o fim do semestre trouxe gargalos com outros projetos acadêmicos e TCC, exigindo repriorização das tarefas e reduzindo o tempo disponível para focar exclusivamente no StudyRats.

---

## Lições Aprendidas

A equipe aprendeu que um bom planejamento das tarefas antes do início da Sprint facilita o desenvolvimento em paralelo e reduz bloqueios entre os membros.

Também foi possível perceber que dividir as histórias em cartões menores ajuda no acompanhamento pelo Kanban, na priorização das entregas e na identificação mais rápida dos riscos.

Para próximas sprints, a equipe buscaria antecipar tarefas mais complexas, reservar mais tempo para testes e ajustes finais e manter uma priorização mais rígida desde o começo.

---

## Pendências

Nenhuma história de usuário ficou pendente na Sprint 2.

Durante a Sprint, algumas tarefas ficaram concentradas na reta final, principalmente por causa da menor disponibilidade dos membros no fim do semestre e da necessidade de conciliar o projeto com outras entregas acadêmicas e TCC.

Entretanto, a equipe priorizou tarefas críticas e conseguiu concluir todas as entregas planejadas.

A Sprint 2 foi encerrada sem pendências finais.

---

## Conclusão

A Sprint 2 encerrou o semestre com a entrega das funcionalidades de gamificação, feedback imediato e acompanhamento de streaks.

As histórias planejadas foram concluídas, os critérios de aceite foram validados e os riscos foram acompanhados até o fechamento da Sprint.

O projeto StudyRats evoluiu de uma plataforma básica de acompanhamento de estudos para uma aplicação com recursos de motivação, constância e engajamento do usuário.
