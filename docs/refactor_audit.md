# Refactor Audit

## Escopo
Refatoracao brownfield incremental, sem reescrever do zero.

## Fase 8 - Atualizacao documental de consolidacao

### Diagnostico
A implementacao das fases anteriores estava concluida, mas havia divergencia entre estado real
de producao e documentacao (champion ativo, nomenclatura tecnica e fronteiras operacionais).

### Patch/Refactor aplicado
Arquivos alterados:
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md
- README.md
- README_ML.md

Mudancas-chave:
- Alinhamento do champion atual para neural_challenger_v1 no texto arquitetural.
- Consolidacao de backend HTTP oficial, frontend oficial e fronteiras src/research/scripts/artifacts.
- Remocao de nomenclatura de marketing em favor de identificadores tecnicos e governanca de modelos.

### Testes
Executado:
- python -m pytest tests/contract/test_manager_registry_runtime_contract.py tests/integration/test_model_health_api_contract.py -q

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md
- README.md
- README_ML.md

### Riscos remanescentes
- Persistencia de alerta critico de calibracao (ECE) no champion atual.
- Necessidade de suite walk-forward formal para governanca de promocoes futuras.

### Classificacao nesta fase
- KEEP:
  - docs/decision_log.md
  - docs/architecture.md
  - docs/refactor_audit.md
  - README.md
  - README_ML.md
- MOVE TO RESEARCH:
  - sem mudanca nesta fase
- MOVE TO LEGACY:
  - sem mudanca nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 9 - Governanca operacional do champion

### Diagnostico
Com o wiring ao registry concluido, faltavam controles operacionais para:
- rollback rapido de promocao,
- dry-run de promocao,
- monitoramento online de calibracao/drift proxy,
- gate estrutural de dependencias para CI.

### Patch/Refactor aplicado
Arquivos alterados:
- src/models/model_registry.py
- data/model_registry.json
- src/analysis/manager_ai.py
- src/api/server.py

Arquivos criados:
- scripts/model_registry_cli.py
- scripts/check_model_health.py
- src/monitoring/model_health.py
- tests/contract/test_dependency_structure_gate.py
- tests/contract/test_registry_rollback_and_adapter_contract.py
- tests/integration/test_model_health_api_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_registry_rollback_and_adapter_contract.py tests/contract/test_dependency_structure_gate.py tests/integration/test_model_health_api_contract.py -q
- python -m pytest tests -q

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Monitoramento de drift ainda baseado em proxy de delta de ECE entre relatórios.
- Runtime adapter hoje contempla adapters existentes (ensemble/neural).

### Classificacao nesta fase
- KEEP:
  - src/models/model_registry.py
  - src/analysis/manager_ai.py
  - src/monitoring/model_health.py
  - scripts/model_registry_cli.py
  - scripts/check_model_health.py
  - tests/contract/test_dependency_structure_gate.py
  - tests/contract/test_registry_rollback_and_adapter_contract.py
  - tests/integration/test_model_health_api_contract.py
- MOVE TO RESEARCH:
  - sem mudanca nesta fase
- MOVE TO LEGACY:
  - sem mudanca nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 8 - Wiring do ManagerAI ao ModelRegistry

### Diagnostico
O registry de champion/challenger existia, mas o runtime de inferencia ainda era fixo
(Ensemble principal + Neural auxiliar), sem respeitar o estado de data/model_registry.json.

### Patch/Refactor aplicado
Arquivo alterado:
- src/analysis/manager_ai.py
  - leitura de ModelRegistry no bootstrap do ManagerAI
  - resolucao de runtime_champion_id e runtime_challenger_id
  - line selection e consenso baseados em champion/challenger efetivos
  - fallback seguro para papeis legados quando registry indisponivel

Arquivos criados:
- tests/contract/test_manager_registry_runtime_contract.py
- tests/unit/test_manager_registry_wiring.py

### Testes
Executado:
- python -m pytest tests/contract/test_manager_registry_runtime_contract.py tests/unit/test_manager_registry_wiring.py -q
- python -m pytest tests -q

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Mapeamento por model_id ainda cobre apenas modelos atuais.
- Estrategia de rollout/promocao operacional (dry-run/rollback) segue para fase seguinte.

### Classificacao nesta fase
- KEEP:
  - src/analysis/manager_ai.py
  - src/models/model_registry.py
  - tests/contract/test_manager_registry_runtime_contract.py
  - tests/unit/test_manager_registry_wiring.py
- MOVE TO RESEARCH:
  - sem mudanca nesta fase
- MOVE TO LEGACY:
  - sem mudanca nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 7 - Limpeza de artefatos e scripts orfaos

### Diagnostico
src/scripts ainda concentrava scripts sem referencia no runtime operacional, e o workspace operacional
mantinha artefatos transitorios de execucao local (pid/log/cache old).

### Patch/Refactor aplicado
Arquivos movidos:
- src/scripts/backtest_system.py -> research/scripts/backtest_system.py
- src/scripts/cleanup_zombies.py -> research/scripts/cleanup_zombies.py
- src/scripts/force_clear_pending.py -> research/scripts/force_clear_pending.py
- src/scripts/list_pending.py -> research/scripts/list_pending.py
- src/scripts/scientific_validation.py -> research/scripts/scientific_validation.py
- src/scripts/validate_health.py -> research/scripts/validate_health.py
- src/scripts/verify_reproducibility.py -> research/scripts/verify_reproducibility.py

Artefatos removidos:
- web_app/.scanner.pid
- logs/system.log
- web_app/.next/cache/webpack/server-development/index.pack.gz.old
- web_app/.next/cache/webpack/client-development/index.pack.gz.old

Arquivos alterados:
- tests/contract/test_runtime_boundaries_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py -q
- python -m pytest tests -q

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Scripts de research permanecem executaveis manualmente (fora do runtime oficial).
- Conteudo de backups/ foi preservado por rastreabilidade historica.

### Classificacao nesta fase
- KEEP:
  - src/scripts/save_production_calibrator.py
  - tests/contract/test_runtime_boundaries_contract.py
- MOVE TO RESEARCH:
  - research/scripts/backtest_system.py
  - research/scripts/cleanup_zombies.py
  - research/scripts/force_clear_pending.py
  - research/scripts/list_pending.py
  - research/scripts/scientific_validation.py
  - research/scripts/validate_health.py
  - research/scripts/verify_reproducibility.py
- MOVE TO LEGACY:
  - sem mudanca nesta fase
- DELETE:
  - artefatos transitorios locais listados acima

## Fase 6 - Mover experimentos para research/

### Diagnostico
Os modulos de pesquisa estavam classificados como MOVE TO RESEARCH, mas ainda localizados dentro de
src/, o que mantinha risco de import acidental por componentes operacionais.

### Patch/Refactor aplicado
Arquivos movidos:
- src/analysis/drift_check.py -> research/analysis/drift_check.py
- src/analysis/stationarity.py -> research/analysis/stationarity.py
- src/scripts/backtest_model.py -> research/scripts/backtest_model.py
- src/scripts/audit_stationarity.py -> research/scripts/audit_stationarity.py
- src/scripts/audit_calibration_ece.py -> research/scripts/audit_calibration_ece.py

Arquivos criados:
- research/__init__.py
- research/analysis/__init__.py
- research/scripts/__init__.py

Arquivos alterados:
- tests/contract/test_runtime_boundaries_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py -q
- python -m pytest tests -q

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- research/ ainda nao possui suite dedicada separada da suite operacional.
- Wiring do registry no ManagerAI segue pendente (fase seguinte).

### Classificacao nesta fase
- KEEP:
  - research/analysis/drift_check.py
  - research/analysis/stationarity.py
  - research/scripts/backtest_model.py
  - research/scripts/audit_stationarity.py
  - research/scripts/audit_calibration_ece.py
- MOVE TO RESEARCH:
  - concluido (movimento fisico realizado)
- MOVE TO LEGACY:
  - sem mudanca nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 5 - Registry Champion-Challenger e Politica de Promocao

### Diagnostico
ProfessionalPredictor (Ensemble) e NeuralChallenger (MLP) eram instanciados diretamente no
ManagerAI.__init__ sem nenhum mecanismo formal de:
- identificacao de qual modelo e o champion de producao,
- criterios documentados e verificaveis para promocao de um challenger,
- trilha de auditoria registrando eventos historicos de troca de champion.

Ausencia de registry tornava impossivel auditar qual modelo gerou cada predicao em producao.

### Patch/Refactor aplicado
Arquivos criados:
- src/models/model_registry.py
  ModelRole enum (CHAMPION/CHALLENGER/RETIRED)
  ModelRecord dataclass (id, name, role, artifact_paths, registered_at, metrics)
  PromotionPolicy (min_brier_improvement_pct=3.0, min_log_loss_improvement_pct=3.0, min_eval_matches=150)
  ModelRegistry (get_champion, get_challengers, is_eligible_for_promotion, promote, register, update_metrics)
- data/model_registry.json
  Bootstrap com estado atual: ensemble_v1=CHAMPION, neural_challenger_v1=CHALLENGER
  Dois eventos REGISTERED no audit_trail inicial
- tests/contract/test_champion_challenger_registry_contract.py
  22 testes de contrato em 4 classes

Arquivos alterados:
- Nenhum arquivo de producao existente foi alterado (registry e contrato sao aditivos).

### Testes
Executado:
- python -m pytest tests/contract/test_champion_challenger_registry_contract.py -v

Resultado:
- 22 passed in 0.20s

Suite completa:
- 85 passed, 184 warnings in 5.55s  (baseline anterior: 63 passed)

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- ManagerAI nao consulta o registry ainda; o wiring sera Fase 6.
- Metricas de ambos os modelos no bootstrap sao null — policy de metricas so bloqueia quando ambos
  os lados tiverem valores medidos. Enquanto null, apenas n_eval_matches e exigido.
- registry.promote() nao e chamado automaticamente; ainda requer invocacao manual ou script de avaliacao.

### Classificacao nesta fase

| Arquivo | Classificacao | Motivo |
|---|---|---|
| src/models/model_registry.py | KEEP | Novo modulo operacional do registry |
| data/model_registry.json | KEEP | Fonte de verdade do estado dos modelos |
| tests/contract/test_champion_challenger_registry_contract.py | KEEP | Contrato fase 5 |

## Fase 1 - Testes de Caracterizacao

### Diagnostico
A base tinha cobertura parcial para contratos internos, mas faltavam testes focados em:
- contrato do backend HTTP oficial,
- contrato da pipeline canonica de features,
- contrato de entrypoints criticos para operacao.

### Patch/Refactor aplicado
Arquivos criados:
- tests/integration/test_api_predictions_contract.py
- tests/contract/test_feature_pipeline_contract.py
- tests/contract/test_entrypoints_contract.py
- tests/unit/ (estrutura)
- tests/integration/ (estrutura)
- tests/contract/ (estrutura)
- tests/walkforward/ (estrutura)

Arquivos alterados:
- requirements.txt (adicionado httpx)

### Testes
Executado:
- python -m pytest tests/contract tests/integration/test_api_predictions_contract.py -q

Resultado:
- 7 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Sem cobertura de contrato para rotas Next.js que executam subprocess.
- Sem suite walk-forward ainda implementada.
- Sem cobertura de consolidacao de entrypoints (sera Fase 2).

## Classificacao de destino nesta fase
- KEEP:
  - src/api/server.py
  - src/features/feature_store.py
  - src/analysis/manager_ai.py
- MOVE TO RESEARCH:
  - nao aplicado nesta fase
- MOVE TO LEGACY:
  - nao aplicado nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 2 - Consolidacao de Entrypoints

### Diagnostico
Havia duplicacao na orquestracao operacional e launcher com path hardcoded, alem de risco de inicializacao duplicada do frontend.

### Patch/Refactor aplicado
Arquivos criados:
- scripts/system_entrypoint.py
- tests/unit/test_system_entrypoint.py

Arquivos alterados:
- start_system.py
- START_DASHBOARD.bat
- tests/contract/test_entrypoints_contract.py

### Testes
Executado:
- python -m pytest tests/contract tests/unit/test_system_entrypoint.py -q
- python -m pytest tests -q

Resultado esperado nesta fase:
- Suite verde apos consolidacao de entrypoints.

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Fluxos de serving paralelos ainda existem (FastAPI/Flask/Next subprocess).
- Rotas Next.js ainda usam subprocess para operacoes de dominio.

## Classificacao de destino nesta fase
- KEEP:
  - scripts/system_entrypoint.py
  - start_system.py (wrapper de compatibilidade)
  - START_DASHBOARD.bat (launcher operacional)
- MOVE TO RESEARCH:
  - nao aplicado nesta fase
- MOVE TO LEGACY:
  - nao aplicado nesta fase
- DELETE:
  - nao aplicado nesta fase

## Fase 3 Lote 1 - Consolidacao de Serving HTTP

### Diagnostico
As rotas web de dominio ainda usavam subprocess para executar scripts Python, inclusive com paths hardcoded, elevando risco operacional e acoplamento entre camadas.

### Patch/Refactor aplicado
Arquivos alterados:
- src/api/server.py
- web_app/app/api/auth/route.ts
- web_app/app/api/bankroll/route.ts
- web_app/app/api/feed/route.ts
- web_app/app/api/leaderboard/route.ts
- web_app/app/api/performance/route.ts

Arquivos criados:
- tests/integration/test_api_serving_consolidation.py

### Testes
Executado:
- python -m pytest tests/integration/test_api_predictions_contract.py tests/integration/test_api_serving_consolidation.py tests/contract/test_entrypoints_contract.py -q
- python -m pytest tests -q

Resultado:
- 56 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Rotas scanner/control, system-status e validate-bets ainda usam subprocess/exec.
- Dependencia do provider em web_app/lib permanece no backend oficial.

## Classificacao de destino nesta fase
- KEEP:
  - src/api/server.py
  - web_app/app/api/auth/route.ts
  - web_app/app/api/bankroll/route.ts
  - web_app/app/api/feed/route.ts
  - web_app/app/api/leaderboard/route.ts
  - web_app/app/api/performance/route.ts
- MOVE TO RESEARCH:
  - nao aplicado neste lote
- MOVE TO LEGACY:
  - nao aplicado neste lote
- DELETE:
  - nao aplicado neste lote

## Fase 3 Lote 2 - Fechamento de Serving HTTP Operacional

### Diagnostico
Ainda existiam rotas Next.js com subprocess/exec para scanner, controle de scanner, system-status e validacao de apostas, mantendo acoplamento operacional no BFF.

### Patch/Refactor aplicado
Arquivos alterados:
- src/api/server.py
- web_app/app/api/scanner/route.ts
- web_app/app/api/scanner/control/route.ts
- web_app/app/api/system-status/route.ts
- web_app/app/api/validate-bets/route.ts
- tests/integration/test_api_serving_consolidation.py

### Testes
Executado:
- python -m pytest tests/integration/test_api_serving_consolidation.py tests/integration/test_api_predictions_contract.py tests/contract/test_entrypoints_contract.py -q
- python -m pytest tests -q

Resultado:
- 58 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Controle de scanner em loop ainda usa processo separado (PID/taskkill), agora centralizado no backend oficial.
- Dependencia de DashboardDataProvider em web_app/lib ainda presente em src/api/server.py.

## Classificacao de destino nesta fase
- KEEP:
  - src/api/server.py
  - web_app/app/api/scanner/route.ts
  - web_app/app/api/scanner/control/route.ts
  - web_app/app/api/system-status/route.ts
  - web_app/app/api/validate-bets/route.ts
  - tests/integration/test_api_serving_consolidation.py
- MOVE TO RESEARCH:
  - nao aplicado neste lote
- MOVE TO LEGACY:
  - nao aplicado neste lote
- DELETE:
  - nao aplicado neste lote

## Fase 4 Lote 1 - Consolidacao da Pipeline Canonica de Features

### Diagnostico
Apesar da inferencia principal ja delegar ao FeatureStore, os fluxos operacionais de treino e calibracao ainda usavam create_advanced_features diretamente, mantendo caminhos paralelos de geracao de features.

### Patch/Refactor aplicado
Arquivos alterados:
- src/training/trainer.py
- scripts/train_model.py
- src/scripts/save_production_calibrator.py
- src/ml/calibration.py
- tests/contract/test_feature_pipeline_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_feature_pipeline_contract.py tests/test_feature_store.py -q
- python -m pytest tests -q

Resultado:
- 60 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Imports diretos de create_advanced_features ainda existem em modulos de analise/research (escopo nao operacional).
- Warning de fragmentacao de DataFrame em features_v2 permanece como debito de performance.

## Classificacao de destino nesta fase
- KEEP:
  - src/features/feature_store.py
  - src/training/trainer.py
  - scripts/train_model.py
  - src/scripts/save_production_calibrator.py
  - src/ml/calibration.py
  - tests/contract/test_feature_pipeline_contract.py
- MOVE TO RESEARCH:
  - modulos de analise que ainda usam create_advanced_features diretamente (pendente de classificacao no Lote 2)
- MOVE TO LEGACY:
  - nao aplicado neste lote
- DELETE:
  - nao aplicado neste lote

## Fase 4 Lote 2 - Consolidacao Operacional Adicional

### Diagnostico
Persistiam pontos de entrada operacionais usando create_advanced_features diretamente: treino neural e helper legado em model_v2.

### Patch/Refactor aplicado
Arquivos alterados:
- src/ml/train_neural.py
- src/models/model_v2.py
- tests/contract/test_feature_pipeline_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_feature_pipeline_contract.py tests/test_feature_store.py -q
- python -m pytest tests -q

Resultado:
- 61 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- src/analysis/* e src/scripts/audit_* ainda usam create_advanced_features por escopo de pesquisa.
- src/web/* legado ainda referencia caminho de features antigo fora do backend oficial.

## Classificacao de destino nesta fase
- KEEP:
  - src/features/feature_store.py
  - src/ml/train_neural.py
  - src/models/model_v2.py
  - tests/contract/test_feature_pipeline_contract.py
- MOVE TO RESEARCH:
  - src/analysis/drift_check.py
  - src/analysis/stationarity.py
  - src/scripts/backtest_model.py
  - src/scripts/audit_stationarity.py
  - src/scripts/audit_calibration_ece.py
- MOVE TO LEGACY:
  - src/web/server.py
  - src/web/scanner_manager.py
- DELETE:
  - artefatos gerados e outputs de execucao quando sem uso comprovado (fora deste patch)

## Fase 4 Lote 3 - Fronteira Operacional x Research/Legacy

### Diagnostico
A classificacao KEEP/MOVE/LEGACY estava definida, mas faltava contrato automatizado para evitar import acidental de modulos research/legacy no runtime operacional.

### Patch/Refactor aplicado
Arquivos alterados:
- src/analysis/drift_check.py
- src/analysis/stationarity.py
- src/scripts/backtest_model.py
- src/scripts/audit_stationarity.py
- src/scripts/audit_calibration_ece.py
- src/web/server.py
- src/web/scanner_manager.py

Arquivos criados:
- tests/contract/test_runtime_boundaries_contract.py

### Testes
Executado:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py tests/contract/test_feature_pipeline_contract.py -q
- python -m pytest tests -q

Resultado:
- 63 passed

### Documentacao atualizada
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md

### Riscos remanescentes
- Contrato atual valida acoplamento por inspeção textual; nao substitui gate de CI com analise de dependencia estrutural.
- Warnings de performance em features_v2 permanecem.

## Classificacao de destino nesta fase
- KEEP:
  - src/features/feature_store.py
  - src/training/trainer.py
  - src/ml/train_neural.py
  - src/models/model_v2.py
  - src/api/server.py
  - tests/contract/test_runtime_boundaries_contract.py
- MOVE TO RESEARCH:
  - src/analysis/drift_check.py
  - src/analysis/stationarity.py
  - src/scripts/backtest_model.py
  - src/scripts/audit_stationarity.py
  - src/scripts/audit_calibration_ece.py
- MOVE TO LEGACY:
  - src/web/server.py
  - src/web/scanner_manager.py
- DELETE:
  - nenhum arquivo removido neste lote
