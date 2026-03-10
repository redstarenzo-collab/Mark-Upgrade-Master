# Roadmap - Mark Upgrade Master

## 1) Visao do Produto
Construir o **Mark** como um gravador e executor de automacoes desktop (macro/RPA leve), com foco em:
- Gravacao de acoes de mouse/teclado/scroll
- Organizacao por **Nodes** (cada Node = conjunto de acoes)
- Reproducao confiavel
- Integracao com CSV
- Geracao de codigo Python

## 2) Estado Atual (Resumo de Problemas)
- Arquitetura baseada em variaveis globais, com risco de bugs e baixa manutenibilidade.
- Conceito de Node implementado de forma incorreta (lista mostra acoes, nao conjuntos).
- Fluxo de gravacao/replay com riscos de concorrencia e controle incompleto de pausa/parada.
- CSV/header com conflito de logica (headers reais vs placeholders "Header 1/2").
- Undo/redo incompleto.
- "Clear" nao limpa todo o estado esperado.
- Traducao parcial/inconsistente.
- Falta captura de scroll.
- Caminhos hardcoded (ex.: icone local) quebram portabilidade.
- Ausencia de estrutura de projeto para escala (modulos/testes/persistencia).

## 3) Objetivo do MVP
Entregar uma versao **estavel e utilizavel** para gravar, editar e reproduzir automacoes simples com CSV.

### Importante sobre execucao sem bloquear o usuario
Para automacao desktop baseada em UI (click/teclado com `pyautogui`), **nao e confiavel** executar no mesmo desktop e esperar que o usuario use a maquina ao mesmo tempo.

Modelo recomendado:
- `Modo Assistido (local)`: roda no desktop atual, ideal para automacoes curtas.
- `Modo Isolado (recomendado para carga massiva)`: roda em VM/maquina secundaria/sessao dedicada.
- `Modo API/Headless` (quando possivel): evita GUI e permite alta escala sem interferir no usuario.

### Escopo minimo do MVP
- Modelo de dados de Node real.
- Gravacao de click, tecla e scroll.
- Replay com start/pause/stop funcionando.
- Importacao CSV confiavel e seletor de colunas funcional.
- Geracao de codigo Python basica por Node.
- Limpeza total de estado (clear completo).
- Salvar/carregar projeto em JSON.

## 4) Roadmap por Fases

## Fase 0 - Fundacao Tecnica (1-2 dias)
**Meta:** preparar base para evolucao sem quebrar.

### Tarefas
- Remover dependencia de estado global e centralizar estado em uma classe/modelo.
- Definir estruturas:
  - `Action(type, payload, delay)`
  - `Node(id, name, actions, repeat, csv_binding)`
  - `Project(nodes, settings)`
- Organizar codigo em modulos (mesmo que no inicio em arquivos simples):
  - `ui.py`, `recorder.py`, `replay.py`, `models.py`, `project_io.py`

### Entregaveis
- Estrutura de classes criada.
- Aplicacao ainda abre e UI principal continua funcional.

### Criterio de pronto
- Sem uso de variaveis globais criticas para estado principal.

## Fase 1 - Core do MVP (3-5 dias)
**Meta:** fluxo principal funcionando de ponta a ponta.

**Status:** Concluida em 2026-03-10 13:41:59

### Tarefas
- [x] Implementar gravacao robusta:
  - [x] click, press e scroll
  - [x] start/pause/stop confiaveis
- [x] Ajustar lista para mostrar **Nodes** e nao acoes individuais.
- [x] Corrigir replay com controle de pausa/retomada/parada.
- [x] Corrigir `Clear` para limpar:
  - [x] nodes
  - [x] preview
  - [x] terminal
  - [x] undo/redo
  - [x] estado temporario de gravacao
- [x] Corrigir importacao CSV e binding de header/colunas.
- [x] Ligar `time_sleep_selector` ao valor real de delay.

### Entregaveis
- [x] Gravacao e execucao basica estaveis.
- [x] CSV importado sem sobreposicao de headers.
- [x] Clear completo funcionando.

### Criterio de pronto
- Usuario consegue gravar um Node, reproduzir e limpar tudo sem reiniciar app.

## Fase 2 - Persistencia e Edicao (2-4 dias)
**Meta:** tornar o app pratico para uso diario.

**Status:** Concluida tecnicamente em 2026-03-10 13:52:51 (validacao manual de fluxo GUI pendente)

### Tarefas
- [x] Salvar/carregar projeto (`.json`).
- [x] Melhorar edicao de acoes no preview com parser resiliente.
- [x] Corrigir undo/redo real (com stack consistente).
- [x] Melhorar tratamento de erro e mensagens no terminal.

### Entregaveis
- [x] Projeto pode ser fechado e retomado sem perda de fluxo.
- [x] Edicao de acoes nao quebra facilmente.

### Criterio de pronto
- Fluxo de criar, salvar, reabrir e executar automacao funciona sem regressao.

## Fase 3 - UX e Identidade Visual (3-5 dias)
**Meta:** elevar percepcao de produto e clareza de estados.

**Status:** Em andamento com regressao funcional em placeholder/target (revisao critica aberta em 2026-03-10 16:03:31)

### Tarefas
- [x] Intro de abertura com personagem Mark.
- [x] Indicador visual de estado (executando, pausado, editando).
- [x] Cubo holografico no canto inferior direito:
  - [x] gira durante gravacao
  - [x] para quando pausado
  - [x] sem fundo e menor tamanho
- [x] Inserir logo na interface (identidade MARK no header).
- [x] Melhorar dark mode (incluindo barras de rolagem escuras).
- [x] Melhorar overlay de gravacao (contraste alto, painel sempre visivel).
- [x] Feedback visual de alvo/placeholder (pulse e marcador na tela).
- [x] Ferramenta `Move Target` com pausa automatica da gravacao.
- [ ] Revisar e estabilizar fluxo de placeholders/target (bug atual em selecao/captura em qualquer area).
- [ ] Completar traducao (menus superiores, secoes e mensagens faltantes).

### Entregaveis
- UI com feedback visual de status.
- Visual consistente em claro/escuro.
- Fluxo de placeholder/target estavel e previsivel em campos de texto e clique geral.

### Criterio de pronto
- Usuario entende estado da automacao sem depender apenas de logs.
- Usuario consegue definir/mover target e inserir placeholders CSV sem falhas de captura.

## Fase 4 - Produto Mais Completo (continuo)
**Meta:** qualidade para distribuicao e escala.

### Tarefas
- Testes unitarios (parser, replay planner, CSV mapper).
- Logging estruturado em arquivo.
- Exportacao de script Python mais robusta (por Node/fluxo).
- Empacotamento com PyInstaller e instrucoes de distribuicao.
- Hardening de seguranca e paths portaveis.
- Suporte a execucao em worker remoto (agente Mark Runner em VM).
- Fila de execucoes (jobs) com status: pendente, executando, concluido, falha.
- Politica de retry e timeout por job.
- Captura de evidencias por execucao (logs, screenshots, video opcional).

### Entregaveis
- Build executavel.
- Base de testes minima.
- Menor risco de regressao.
- Pipeline para execucao massiva sem bloquear o desktop do operador.

### Criterio de pronto
- App instalavel e reproduzivel em outra maquina com setup documentado.

## 5) Backlog Priorizado (Now / Next / Later)

### Now (MVP imediato)
- [x] Modelo real de Node
- [x] Gravacao com scroll
- [x] Replay confiavel com pausa/parada
- [x] CSV/header corrigido
- [x] Clear total
- [x] Persistencia JSON
- [ ] Revisao critica placeholder/target (captura e aplicacao)

### Next
- [x] Undo/redo robusto
- [x] Parser de preview resiliente
- [ ] Traducao completa
- [ ] Correcao dark mode (scrollbars)
- [ ] Validacao guiada do fluxo CSV end-to-end (importar, ancorar placeholder, replay com preenchimento)

## 11) Revisao Critica Aberta - Placeholder/Target
**Aberta em:** 2026-03-10 16:03:31

### Problemas reportados
- Placeholder registrado no node, mas comportamento inconsistente no preenchimento durante execucao.
- Captura de target nao confiavel em "qualquer ponto da tela".
- `Move Target` com experiencia lenta/instavel em alguns contextos.

### Plano de correcao
- Revisar fluxo de captura de mouse com telemetria de eventos (click/move ignorado/aceito).
- Definir criterio unico de "area ignorada" (somente overlays da ferramenta).
- Garantir update imediato de coordenadas em qualquer clique valido.
- Validar comportamento especifico em campos de texto (cursor I-beam).
- Fechar com checklist manual: import CSV -> selecionar target -> placeholder -> replay preenchendo colunas.

### Criterio de fechamento
- 100% dos testes manuais do fluxo CSV/placeholder/target passam sem regressao.

### Later
- [ ] Intro + animacoes do Mark
- [ ] Cubo holografico reativo
- [ ] Empacotamento e testes automatizados
- [ ] Mark Runner em VM/sessao isolada
- [ ] Fila de jobs para execucao em lote

## 6) Riscos e Mitigacoes
- **Concorrencia com listeners e UI (Qt):** usar sinais/slots para atualizar interface apenas na thread principal.
- **Fragilidade de parser textual:** adotar formato estruturado interno (modelo), usando preview apenas como visualizacao/edicao assistida.
- **Dependencia de ambiente (PyQt5/pynput/pyautogui):** fixar `requirements.txt` e versoes testadas.
- **Portabilidade Windows:** remover paths fixos e detectar recursos por caminho relativo.
- **Interferencia com usuario durante execucao:** para cargas massivas, executar em ambiente isolado (VM, outra maquina ou sessao dedicada).
- **Escalabilidade limitada por automacao de tela:** priorizar integracoes por API/headless sempre que disponivel.

## 8) Arquitetura para Execucao Massiva (sem bloquear usuario)
### Opcao A - Runner em VM (recomendada)
- App principal so agenda jobs.
- Um ou mais "Mark Runner" executam automacoes em VMs dedicadas.
- Usuario segue usando a maquina local sem interferencia.

### Opcao B - Segunda maquina fisica
- Mesmo conceito da VM, com custo operacional maior.

### Opcao C - Mesmo PC (nao recomendado para automacao GUI)
- Possivel apenas com severas limitacoes.
- Qualquer interacao do usuario pode quebrar a automacao.

### Requisitos minimos para essa arquitetura
- Formato de projeto portavel (`.json`) para envio ao runner.
- Executor desacoplado da interface (CLI/servico).
- Fila de jobs + historico + monitoramento de status.
- Coleta de evidencias (logs/screenshot) por job.

## 9) Visao Futura - Modulo Mark Runner Cloud
### Conceito
No estagio posterior ao MVP, criar o modulo `Mark Runner` como oferta premium: ao contratar o plano, o usuario ganha direito de executar automacoes em infraestrutura isolada na nuvem.

### Provedores alvo
- AWS
- Microsoft Azure
- Google Cloud

### Modelo de produto (futuro)
- App Mark (desktop) para criar/editar automacoes.
- Mark Runner Cloud para executar jobs em VM dedicada do cliente.
- Painel de status com consumo, historico, logs e evidencias.

### Regras de negocio iniciais (proposta)
- Licenca define quantidade de runners simultaneos.
- Cada runner tem cota de horas de execucao por mes.
- Upgrade de plano libera mais capacidade (concorrencia e tempo).

### Observacoes
- Este modulo entra **depois do MVP** e depende de autenticacao, faturamento e orquestracao de infraestrutura.
- Primeiro validar produto com runner local/VM manual; depois evoluir para provisionamento automatizado em nuvem.

## 7) Definicao de Sucesso
O MVP sera considerado pronto quando:
- Um usuario consegue gravar pelo menos 1 Node com click/tecla/scroll.
- Consegue executar com pause/resume/stop sem travar.
- Consegue importar CSV e usar coluna selecionada sem conflito.
- Consegue limpar tudo e reiniciar fluxo dentro da mesma sessao.
- Consegue salvar e reabrir o projeto mantendo os Nodes.

## 10) Log de Execucao
- 2026-03-10 13:41:59 - Fase 1 concluida (gravacao click/press/scroll, replay com pausa/parada, clear completo, CSV/header corrigido, delay conectado ao seletor).
- 2026-03-10 13:52:51 - Fase 2 concluida tecnicamente (salvar/carregar JSON, parser resiliente no preview, undo/redo com snapshot consistente, mensagens de erro aprimoradas).
- 2026-03-10 13:58:28 - Fase 3 iniciada com identidade visual MARK (intro, status chip, painel de sinal, cubo holografico animado, tema dark/light refinado).
- 2026-03-10 14:00-16:00 - Iteracoes de UX/controle: overlay de gravacao destacado, integracao de placeholders CSV no painel, pulse visual de target/placeholder, modo `Move Target`, ajustes de status `IDLE` e iconografia no header.
- 2026-03-10 16:03:31 - Aberta revisao critica de placeholder/target por inconsistencias no fluxo real de captura/preenchimento.

---
Ultima atualizacao: 2026-03-10 16:03:31
