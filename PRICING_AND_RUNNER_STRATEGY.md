# Pricing and Runner Strategy - Mark

## 1) Objetivo
Definir uma estrategia comercial e tecnica para:
- `Mark Padrao` (desktop): criacao e execucao local de automacoes.
- `Mark Runner Cloud`: execucao isolada em VM para escala sem bloquear a maquina do usuario.

Este documento e para **fase pos-MVP**.

## 2) Principios de Produto
- Simplicidade: cliente entende rapido o que esta comprando (desktop base + cloud opcional).
- Previsibilidade: limites claros de uso e custos controlados.
- Escalabilidade: capacidade de aumentar execucoes por plano.
- Confiabilidade: execucao isolada, com log e evidencias.

## 3) Embalagem de Oferta (Padrao + Cloud)
Modelo recomendado em duas camadas:
- `Camada 1 - Mark Padrao (assinatura base)`
- `Camada 2 - Mark Runner Cloud (add-on ou plano avancado)`

Assim, todo cliente paga pelo produto principal e adiciona cloud quando precisar de escala.

## 4) Pricing do Mark Padrao (desktop)
Valores abaixo sao placeholders para validacao comercial.

## Plano Basic (Padrao)
- 1 usuario
- Gravacao/replay local
- Import CSV basico
- Salvar/carregar projetos
- Suporte comunidade/email
- Sem execucao cloud

## Plano Pro (Padrao)
- Ate 3 usuarios
- Tudo do Basic
- Recursos avancados de edicao e organizacao de nodes
- Historico estendido local
- Suporte prioritario
- Sem execucao cloud incluida (cloud opcional como add-on)

## Plano Team (Padrao)
- Ate 10 usuarios
- Tudo do Pro
- Gestao basica de workspace/time
- Permissoes por perfil (admin/editor/viewer)
- Integracoes iniciais
- Cloud opcional ou bundle com franquia inicial

## Add-ons do Mark Padrao
- Assentos extras (usuario adicional)
- Pacote de onboarding/implantacao
- Suporte premium (SLA)
- Bundle com horas iniciais de Runner Cloud

## 5) Unidades de Cobranca do Runner Cloud
Modelo recomendado: cobrar por **capacidade + consumo**.

### Capacidade
- `Runners simultaneos`: quantas automacoes podem rodar ao mesmo tempo.

### Consumo
- `Horas de runner`: tempo total de execucao mensal.
- `Armazenamento de evidencias`: logs, screenshots, artefatos.

## 6) Estrutura de Planos Runner Cloud (proposta inicial)
Valores abaixo sao placeholders para validacao comercial.

## Plano Starter
- 1 runner simultaneo
- 120 horas de runner/mes
- Retencao de evidencias: 7 dias
- Suporte: padrao
- Perfil: pequenos times e validacao inicial

## Plano Growth
- 3 runners simultaneos
- 500 horas de runner/mes
- Retencao de evidencias: 30 dias
- Suporte: prioritario
- Perfil: operacao recorrente com lotes diarios

## Plano Scale
- 10 runners simultaneos
- 2000 horas de runner/mes
- Retencao de evidencias: 90 dias
- Suporte: SLA dedicado
- Perfil: operacoes massivas e multi-time

## Add-ons
- Horas extras de runner
- Runner dedicado (VM exclusiva)
- Retencao estendida de evidencias
- Regiao de nuvem especifica (compliance)

## 7) Politicas de Limite
- Ao atingir limite de horas:
  - opcao A: bloquear novos jobs
  - opcao B: continuar com cobranca por excedente
- Ao atingir limite de concorrencia:
  - jobs entram em fila automaticamente
- Fila por tenant com prioridade configuravel (normal, alta)

## 8) Metrica de Uso (o que medir)
Por organizacao (tenant):
- Jobs enviados por dia
- Taxa de sucesso/falha
- Tempo medio por job
- Horas consumidas no mes
- Picos de concorrencia
- Custo estimado por workflow

Por job:
- `job_id`, `node_id/workflow_id`
- inicio/fim/duracao
- status final (success, failed, timeout, cancelled)
- erro principal
- evidencias associadas (log, screenshot, video opcional)

## 9) Arquitetura Comercial x Tecnica
## Camadas
- `Mark Desktop`: autoria e envio de jobs.
- `Control Plane`: autenticacao, billing, fila, roteamento.
- `Runner Plane`: VMs/sessoes que executam automacoes.

## Fluxo simplificado
1. Usuario cria automacao no desktop.
2. Desktop publica job para API.
3. Control Plane valida licenca e cota.
4. Job e alocado em runner disponivel.
5. Runner executa e envia status + evidencias.
6. Desktop/painel mostra resultado e consumo.

## 10) Estrategia de Custos em Nuvem
- Comecar com 1 provedor principal para reduzir complexidade inicial.
- Usar VMs de perfil compativel com automacao GUI (Windows quando necessario).
- Auto-scale por fila: sobe runners em pico e reduz em ociosidade.
- Definir teto de custo por tenant para evitar surpresas financeiras.

## 11) Fases de Implementacao
## Fase A - Validacao (pos-MVP imediato)
- Runner local/VM manual (sem provisionamento automatico)
- Fila basica de jobs
- Medicao de horas consumidas

## Fase B - Beta Cloud
- Provisionamento semiautomatico em 1 provedor (ex.: Azure ou AWS)
- Dashboard minimo de status e consumo
- Politica de retry/timeout

## Fase C - Escala
- Multi-provedor (AWS/Azure/GCP)
- SLA por plano
- Otimizacao de custo por workload
- Billing completo com fatura e alertas de consumo

## 12) Requisitos de Seguranca
- Isolamento por tenant (credenciais e dados).
- Criptografia em transito e repouso.
- Segredos em cofre (nunca hardcoded).
- Auditoria de acesso e trilha de execucao.
- Politica de retencao e descarte de evidencias.

## 13) Go-to-Market (resumido)
- Posicionamento: "Automacao em escala sem travar o computador do time".
- Entrada: vender Mark Padrao como porta de entrada.
- Prova de valor: comparativo entre execucao local vs Runner Cloud.
- Upsell natural: quando cliente bater limite de horas/concorrencia local.

## 14) Riscos e Mitigacoes
- Custo de nuvem alto: limitar concorrencia por plano e auto-scale conservador.
- Falhas de automacao GUI: evidencias + retry com backoff + timeout.
- Complexidade de billing cedo demais: iniciar com controle simples de cota.
- Suporte operacional: padronizar templates de diagnostico de falha.

## 15) KPIs de Sucesso
- Conversao Free/Basic -> Pro/Team.
- Taxa de sucesso de job >= 95% (excluindo erro de regra de negocio do cliente).
- Tempo medio de fila abaixo do alvo por plano.
- Custo de infraestrutura por hora dentro da margem definida.
- Retencao de clientes apos 90 dias.
- Conversao Starter -> Growth.

## 16) Definicoes Iniciais Recomendadas
- Moeda padrao: BRL (ou USD, conforme mercado alvo).
- Ciclo de cobranca: mensal.
- Trial: 14 dias com limite baixo de horas.
- Excedente: habilitado apenas em Growth/Scale (opcional no Starter).
- Estrategia comercial inicial:
  - Mark Padrao com planos Basic/Pro/Team
  - Runner Cloud vendido como add-on no inicio

---
Ultima atualizacao: 2026-03-10
