# Arquitetura Atual e Direcao de Refatoracao

## Estado Atual (Fase 9)

### Backend HTTP
- Oficial de fato para predições: src/api/server.py
- Endpoints de dashboard no Next.js agora fazem proxy HTTP para backend oficial:
  - /api/predictions
  - /api/auth
  - /api/bankroll
  - /api/feed
  - /api/leaderboard
  - /api/performance
  - /api/scanner
  - /api/scanner/control
  - /api/system-status
  - /api/validate-bets

### Frontend
- Oficial: web_app (Next.js)
- Secundario/nao oficial: src/web/frontend (Vite, legado isolado)

### Entrypoints Operacionais
- Entrypoint consolidado da stack local:
  - scripts/system_entrypoint.py
- Wrapper de compatibilidade mantido:
  - start_system.py
- Launcher Windows portavel:
  - START_DASHBOARD.bat

### Treino e Inferencia
- Inferencia principal: ManagerAI + FeatureStore + ProfessionalPredictor
- Challenger neural coexistente na orquestracao com papeis efetivos via ModelRegistry
- Treino operacional e calibracao operacional usam FeatureStore.get_training_features
- Treino neural operacional e helper legado de model_v2 tambem usam FeatureStore.get_training_features
- Modulos research/legacy marcados explicitamente com classificacao e protegidos por contrato de fronteira de runtime
- Modulos experimentais movidos fisicamente para research/ (fora de src/ operacional)
- Scripts orfaos removidos de src/scripts e consolidados em research/scripts
- Artefatos transitorios de execucao (pid/cache/log local) limpos do workspace operacional
- Registry formal de modelos: data/model_registry.json (neural_challenger_v1=CHAMPION, ensemble_v1=RETIRED)
- Politica de promocao formalizada: min 3% melhoria em Brier+LogLoss, min 150 matches avaliados
- ManagerAI resolve champion/challenger em runtime via registry (com fallback seguro para papeis legados)
- Rollback automatizado de promotion disponivel via ModelRegistry e CLI operacional
- Endpoint oficial de saude de modelo: /api/model-health
- Gate estrutural de dependencias por AST no pacote de contratos
- Challengers ativos devem residir em research/ e so sao promovidos com avaliacao formal reproduzivel

## Principios da Arquitetura-Alvo

1. Um backend HTTP oficial.
2. Um frontend oficial.
3. Uma pipeline canonica de treino.
4. Uma pipeline canonica de inferencia.
5. Uma unica fonte de verdade para features.
6. Um champion de producao; challengers apenas em research com avaliacao formal.

## Decisoes ja aplicadas ate esta fase

- Fase 1: testes de caracterizacao para contratos criticos.
- Fase 2: consolidacao de startup local em modulo unico, com wrapper compativel.
- Fase 3 Lote 1: consolidacao parcial de serving HTTP nas rotas de dominio do dashboard.
- Fase 3 Lote 2: consolidacao das rotas operacionais remanescentes do dashboard em HTTP backend.
- Fase 4 Lote 1: consolidacao da geracao de features de treino/calibracao operacional via FeatureStore.
- Fase 4 Lote 2: extensao da consolidacao para treino neural e wrapper legado de model_v2.
- Fase 4 Lote 3: fronteira explicita entre runtime operacional e modulos research/legacy.
- Fase 5: registry formal champion-challenger com politica de promocao e trilha de auditoria imutavel.
- Fase 6: movimento fisico dos experimentos para research/ e endurecimento do contrato de fronteira.
- Fase 7: limpeza de artefatos e scripts orfaos com guardrail contratual para evitar regressao.
- Fase 8: wiring do ManagerAI ao ModelRegistry para champion/challenger efetivos no runtime.
- Fase 9: governanca operacional (rollback/dry-run/alerts online/gate estrutural CI).

## Controles de Qualidade introduzidos

- Contrato HTTP para endpoint de predições.
- Contrato de delegacao da pipeline de features.
- Contrato de existencia e papel de entrypoints criticos.
- Testes unitarios do entrypoint consolidado.
- Contrato de registry champion-challenger (22 testes: bootstrap, policy, auditoria, persistencia).
- Contrato de fronteira atualizado para exigir experimentos fora de src/.
- Contrato de fronteira atualizado para manter src/scripts apenas com entrypoint operacional.
- Contrato de runtime do registry no ManagerAI + teste unitario de comportamento champion/challenger.
- Contratos de rollback+adapter, endpoint de model health e gate estrutural AST.

## Proxima fase
10: pipeline operacional de treino -> avaliacao -> dry-run promote -> aprovacao -> promote e execucao guiada de scanner para rodada seguinte.
