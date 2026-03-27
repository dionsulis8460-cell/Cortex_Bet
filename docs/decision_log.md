# Decision Log

## 2026-03-27 - Fase 8 (Atualizacao documental de consolidacao)

### DECISION
Atualizar a documentacao oficial para refletir o estado real da arquitetura apos as fases 1-9,
incluindo champion ativo no registry, separacao de fronteiras (src/research/scripts/artifacts),
e remocao de nomenclaturas de marketing em favor de nomes tecnicos.

### CONTEXT
As mudancas de runtime e governanca ja estavam implementadas e testadas, mas havia divergencia
documental em pontos criticos: champion ainda descrito como ensemble em alguns trechos e uso de
nomes de marketing sem aderencia ao contrato arquitetural.

### CHANGES
Arquivos alterados:
- docs/decision_log.md
- docs/architecture.md
- docs/refactor_audit.md
- README.md
- README_ML.md

Atualizacoes principais:
- Estado do champion em producao alinhado para neural_challenger_v1 (adapter neural).
- Formalizacao textual de challengers somente em research/ com avaliacao formal.
- Clarificacao de backend HTTP oficial (FastAPI em src/api/server.py) e frontend oficial (web_app).
- Terminologia tecnica consolidada para componentes e pipeline canonica.

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_manager_registry_runtime_contract.py tests/integration/test_model_health_api_contract.py -q

### RISK
- A promocao real colocou o modelo neural como champion; recomendada reavaliacao walk-forward
  reproduzivel antes de novas promocoes.
- Alerta critico de calibracao (ECE) permanece e requer ciclo de recalibracao dedicado.

### NEXT STEP
Conduzir Fase 10 com pipeline operacional formal (train -> evaluate -> dry-run -> approve -> promote)
e suite walk-forward reproduzivel para validacao de champion/challenger.

## 2026-03-27 - Fase 9 (Governanca Operacional de Champion)

### DECISION
Adicionar governanca operacional ao champion-challenger com:
- rollback automatizado de promocao,
- monitor online com alertas de calibracao/drift proxy,
- gate estrutural de dependencias via AST no CI,
- estrategia de novos model_id sem alteracao manual de codigo via runtime_adapter no registry.

### CONTEXT
Mesmo com wiring do ManagerAI ao registry (Fase 8), faltavam controles operacionais para
reverter promocao rapidamente, monitorar saude do modelo em runtime e evitar acoplamentos
estruturais fora da arquitetura-alvo.

### CHANGES
Arquivos alterados:
- src/models/model_registry.py
  - runtime_adapter por modelo
  - get_runtime_adapter(), get_runtime_roles()
  - preview_promotion() (dry-run)
  - rollback_last_promotion() (reversao automatizada)
- data/model_registry.json
  - runtime_adapter adicionado em ensemble_v1/neural_challenger_v1
- src/analysis/manager_ai.py
  - _model_total_from_id() agora usa runtime_adapter do registry (sem hardcode de IDs)
- src/api/server.py
  - novo endpoint /api/model-health

Arquivos criados:
- scripts/model_registry_cli.py
- scripts/check_model_health.py
- src/monitoring/model_health.py
- tests/contract/test_dependency_structure_gate.py
- tests/contract/test_registry_rollback_and_adapter_contract.py
- tests/integration/test_model_health_api_contract.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_registry_rollback_and_adapter_contract.py tests/contract/test_dependency_structure_gate.py tests/integration/test_model_health_api_contract.py -q
- python -m pytest tests -q

### RISK
- runtime_adapter atualmente suporta adapters existentes (ensemble/neural).
- drift e tratado via proxy de delta de ECE entre relatórios; ainda nao substitui detector de drift estatistico dedicado.

### NEXT STEP
Fase 10 - pipeline operacional de treino+promocao assistida (train -> evaluate -> dry-run promote -> approve -> promote),
e depois execucao de scanner para proxima rodada.

## 2026-03-27 - Fase 8 (Wiring ManagerAI ao ModelRegistry)

### DECISION
Tornar o champion/challenger efetivo no runtime do ManagerAI via ModelRegistry,
com fallback seguro para papeis legados quando o registry estiver indisponivel.

### CONTEXT
O registry (Fase 5) estava implementado, mas ainda nao era usado no fluxo de inferencia.
ManagerAI continuava fixo em Ensemble como principal e Neural como auxiliar, sem respeitar
promocoes registradas em data/model_registry.json.

### CHANGES
Arquivo alterado:
- src/analysis/manager_ai.py
  - import de ModelRegistry
  - _load_registry() com fallback seguro
  - _resolve_runtime_model_roles() para definir runtime_champion_id/runtime_challenger_id
  - _model_total_from_id() para inferencia por model_id conhecido
  - line selection passou de (ensemble, neural) fixo para (champion_raw, challenger_raw)
  - consenso final passou a usar champion_conf no runtime
  - debug/feedback agora exibem champion/challenger ativos

Arquivos criados:
- tests/contract/test_manager_registry_runtime_contract.py
- tests/unit/test_manager_registry_wiring.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_manager_registry_runtime_contract.py tests/unit/test_manager_registry_wiring.py -q
- python -m pytest tests -q

Resultado esperado nesta fase:
- suite verde com comprovacao de wiring textual e comportamental do champion/challenger.

### RISK
- Mapeamento de model_id em runtime esta explicito para os IDs atuais (ensemble_v1 e neural_challenger_v1).
  Novos modelos exigirao extensao em _model_total_from_id().
- PredictionResult mantem campos ensemble_raw/neural_raw por compatibilidade de payload.

### NEXT STEP
Fase 9 - Governanca de promocao operacional (CLI/script com dry-run, validacao de thresholds e
registro de auditoria), alem de exposicao da versao champion ativa na API.

## 2026-03-27 - Fase 7 (Limpeza de Artefatos e Scripts Orfaos)

### DECISION
Limpar artefatos transitorios do workspace operacional e remover scripts orfaos de src/scripts,
consolidando-os em research/scripts com classificacao explicita.

### CONTEXT
Apos Fase 6, o maior acoplamento residual estava em src/scripts com utilitarios sem uso no runtime
operacional. Tambem persistiam artefatos de execucao local (pid/cache/log), sem valor de producao.

### CHANGES
Scripts movidos de src/scripts para research/scripts:
- src/scripts/backtest_system.py -> research/scripts/backtest_system.py
- src/scripts/cleanup_zombies.py -> research/scripts/cleanup_zombies.py
- src/scripts/force_clear_pending.py -> research/scripts/force_clear_pending.py
- src/scripts/list_pending.py -> research/scripts/list_pending.py
- src/scripts/scientific_validation.py -> research/scripts/scientific_validation.py
- src/scripts/validate_health.py -> research/scripts/validate_health.py
- src/scripts/verify_reproducibility.py -> research/scripts/verify_reproducibility.py

Artefatos removidos do workspace operacional:
- web_app/.scanner.pid
- logs/system.log
- web_app/.next/cache/webpack/server-development/index.pack.gz.old
- web_app/.next/cache/webpack/client-development/index.pack.gz.old

Arquivos alterados:
- tests/contract/test_runtime_boundaries_contract.py
  - research_files expandido
  - moved_from_src expandido
  - novo teste: src/scripts contem apenas save_production_calibrator.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py -q
- python -m pytest tests -q

Resultado esperado nesta fase:
- suite verde apos limpeza e guardrails de nao-regressao.

### RISK
- Scripts movidos para research/ podem conter paths operacionais antigos para uso manual.
- Limpeza nao removeu artefatos dentro de backups/ por preservacao historica.

### NEXT STEP
Fase 8 - Wiring do ManagerAI ao ModelRegistry para selecao formal CHAMPION/CHALLENGER em runtime.

## 2026-03-27 - Fase 6 (Mover Experimentos para research/)

### DECISION
Mover fisicamente os modulos classificados como MOVE TO RESEARCH para a arvore research/,
removendo-os de src/ para reforcar separacao entre runtime operacional e codigo experimental.

### CONTEXT
Na Fase 4 Lote 3 os modulos foram apenas classificados por header, mas continuavam em src/,
o que deixava risco de acoplamento acidental via import e dificultava leitura da fronteira.

### CHANGES
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
  - lista de research_files atualizada para research/*
  - forbidden_tokens atualizados para research.*
  - novo teste garantindo ausencia fisica dos modulos em src/

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py -q
- python -m pytest tests -q

Resultado esperado nesta fase:
- suite verde com contrato de fronteira atualizado e sem regressao operacional.

### RISK
- Scripts em research/ continuam executaveis manualmente e podem depender de paths relativos
  antigos; sem impacto no runtime operacional.
- Ainda nao ha CI dedicada para validar research/ isoladamente.

### NEXT STEP
Fase 7 - Wiring do ManagerAI ao ModelRegistry para selecao formal CHAMPION/CHALLENGER em runtime.

## 2026-03-27 - Fase 5 (Registry Champion-Challenger e Politica de Promocao)

### DECISION
Formalizar o registry de modelos com politica de promocao explicita e trilha de auditoria imutavel,
eliminando o acoplamento implicito entre ProfessionalPredictor/NeuralChallenger e o ManagerAI.

### CONTEXT
ProfessionalPredictor (Ensemble) e NeuralChallenger (MLP) coexistiam no ManagerAI.__init__ sem nenhum
mecanismo formal para:
- conhecer qual era o champion de producao,
- registrar criterios de promocao,
- registrar eventos de troca de champion com rastreabilidade.
A ausencia de um registry tornava impossivel auditar historicamente quais modelos rodaram em producao
e por que um challenger foi (ou nao foi) promovido.

### CHANGES
Arquivos criados:
- src/models/model_registry.py  (ModelRole, ModelRecord, PromotionPolicy, ModelRegistry)
- data/model_registry.json      (bootstrap com estado atual: ensemble_v1=CHAMPION, neural_challenger_v1=CHALLENGER)
- tests/contract/test_champion_challenger_registry_contract.py  (22 testes de contrato)

Arquivos alterados:
- Nenhum arquivo de producao alterado neste lote (registry e contrato sao aditivos).

### PROMOTION POLICY (thresholds)
- min_brier_improvement_pct: 3.0  (challenger Brier <= champion_brier * 0.97)
- min_log_loss_improvement_pct: 3.0
- min_eval_matches: 150
- Quando metricas do champion sao null (bootstrap), apenas n_eval_matches e exigido.

### AUDIT TRAIL
- Toda mutacao (REGISTERED, EVALUATED, RETIRED, PROMOTED) e appendada ao campo audit_trail do JSON.
- Nenhum evento e jamais removido (append-only).

### TEST EVIDENCE
Comando executado:
- python -m pytest tests/contract/test_champion_challenger_registry_contract.py -v

Resultado:
- 22 passed in 0.20s

Suite completa:
- 85 passed, 184 warnings in 5.55s  (baseline anterior: 63 passed)

### RISK
- ManagerAI ainda instancia ProfessionalPredictor e NeuralChallenger diretamente; o registry nao e
  consultado no path de inferencia ainda. O wiring sera Fase 6.
- Metricas dos dois modelos no bootstrap sao null (nunca foram medidas formalmente). O registry
  so bloqueia promocao pela politica de metricas quando ambos os lados tiverem valores mensurados.
- Nenhum arquivo foi deletado ou movido neste lote.

### NEXT STEP
Fase 6 - Wiring do ManagerAI ao registry (carregar modelos via registry, respeitar papel CHAMPION/CHALLENGER
na orquestracao de inferencia).

## 2026-03-27 - Fase 1 (Testes de Caracterizacao)

### DECISION
Criar uma rede minima de testes de caracterizacao antes de mover ou apagar codigo de producao.

### CONTEXT
A base possui multiplos entrypoints e camadas paralelas de serving, com risco de regressao funcional durante consolidacao arquitetural.

### CHANGES
- Criado teste de contrato do endpoint HTTP oficial de predições:
  - tests/integration/test_api_predictions_contract.py
- Criado teste de contrato da pipeline canonica de features:
  - tests/contract/test_feature_pipeline_contract.py
- Criado teste de contrato de entrypoints e runtime atual:
  - tests/contract/test_entrypoints_contract.py
- Estrutura de testes por tipo criada para suportar fases seguintes:
  - tests/unit/
  - tests/integration/
  - tests/contract/
  - tests/walkforward/
- Dependencia de teste adicionada para reprodutibilidade:
  - requirements.txt (httpx)

### TEST EVIDENCE
Comando executado:
- python -m pytest tests/contract tests/integration/test_api_predictions_contract.py -q

Resultado:
- 7 passed

### RISK
- Cobertura ainda nao inclui fluxos end-to-end completos de scanner e rotas Next.js que usam subprocess.
- Cobertura de walk-forward ainda nao implementada (apenas estrutura criada).

### NEXT STEP
Fase 2 - consolidar entrypoints sem remover comportamento antes de ampliar caracterizacao para fluxos scanner/orquestracao.

## 2026-03-27 - Fase 2 (Consolidacao de Entrypoints)

### DECISION
Consolidar a orquestracao operacional de stack em um unico modulo tecnico, mantendo compatibilidade com o comando legado.

### CONTEXT
O projeto tinha logica de startup duplicada e launcher com caminho hardcoded, alem de risco de iniciar frontend duas vezes.

### CHANGES
- Criado modulo canonico de orquestracao:
  - scripts/system_entrypoint.py
- Convertido entrypoint legado em wrapper compativel:
  - start_system.py
- Corrigido launcher Windows para ser portavel e evitar startup duplicado do frontend:
  - START_DASHBOARD.bat
- Contratos de entrypoint atualizados:
  - tests/contract/test_entrypoints_contract.py
- Testes unitarios do novo modulo:
  - tests/unit/test_system_entrypoint.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract tests/unit/test_system_entrypoint.py -q
- python -m pytest tests -q

Resultado esperado nesta fase:
- Suite verde apos consolidacao de entrypoints.

### RISK
- Ainda existem entrypoints concorrentes no dominio web legado (src/web/server.py) nao removidos nesta fase.
- Rotas Next.js continuam com subprocess em varias operacoes (sera tratado em Fase 3).

### NEXT STEP
Fase 3 - consolidar serving para um backend HTTP oficial, reduzindo cola via subprocess nas rotas web.

## 2026-03-27 - Fase 3 Lote 1 (Consolidacao de Serving HTTP)

### DECISION
Migrar rotas web de dominio (auth, bankroll, feed, leaderboard e performance) para proxy HTTP no backend oficial FastAPI, removendo subprocess como cola arquitetural nesse escopo.

### CONTEXT
As rotas Next.js executavam scripts Python por spawn/exec, incluindo caminhos hardcoded, aumentando fragilidade operacional e duplicando camada de serving.

### CHANGES
- Backend oficial expandido com endpoints HTTP de dominio:
  - src/api/server.py
    - /api/auth
    - /api/bankroll (GET/POST/DELETE)
    - /api/feed
    - /api/leaderboard
    - /api/performance
- Rotas Next.js migradas de subprocess para fetch HTTP:
  - web_app/app/api/auth/route.ts
  - web_app/app/api/bankroll/route.ts
  - web_app/app/api/feed/route.ts
  - web_app/app/api/leaderboard/route.ts
  - web_app/app/api/performance/route.ts
- Testes de integração para novos contratos de serving:
  - tests/integration/test_api_serving_consolidation.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/integration/test_api_predictions_contract.py tests/integration/test_api_serving_consolidation.py tests/contract/test_entrypoints_contract.py -q
- python -m pytest tests -q

Resultado:
- 56 passed

### RISK
- Rotas scanner/control, validate-bets e system-status ainda usam subprocess/exec.
- src/api/server.py ainda depende de DashboardDataProvider em web_app/lib (acoplamento de camada).

### NEXT STEP
Fase 3 Lote 2 - migrar scanner/control, validate-bets e system-status para HTTP backend e reduzir acoplamento residual.

## 2026-03-27 - Fase 3 Lote 2 (Fechamento do Serving HTTP)

### DECISION
Concluir a migracao das rotas operacionais restantes (scanner, scanner/control, system-status e validate-bets) para proxy HTTP no backend oficial, eliminando subprocess/exec do BFF Next.js nesse escopo.

### CONTEXT
Mesmo apos o Lote 1, ainda havia rotas do dashboard com execucao de scripts Python por spawn/exec, mantendo fragilidade operacional e acoplamento entre camadas.

### CHANGES
- Backend oficial expandido com endpoints operacionais:
  - src/api/server.py
    - /api/scanner (POST)
    - /api/scanner/control (GET/POST)
    - /api/system-status (GET)
    - /api/validate-bets (POST)
- Rotas Next.js migradas para fetch HTTP:
  - web_app/app/api/scanner/route.ts
  - web_app/app/api/scanner/control/route.ts
  - web_app/app/api/system-status/route.ts
  - web_app/app/api/validate-bets/route.ts
- Testes de integracao ampliados para novos contratos:
  - tests/integration/test_api_serving_consolidation.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/integration/test_api_serving_consolidation.py tests/integration/test_api_predictions_contract.py tests/contract/test_entrypoints_contract.py -q
- python -m pytest tests -q

Resultado:
- 58 passed

### RISK
- Controle de scanner em loop no backend ainda depende de processo externo (PID/taskkill), agora centralizado e sem subprocess no Next.js.
- Acoplamento do backend com DashboardDataProvider de web_app/lib permanece como debito tecnico para fase posterior.

### NEXT STEP
Encerrar Fase 3 com hardening dos contratos HTTP e iniciar Fase 4 (consolidacao profunda da pipeline canonica de features treino/inferencia).

## 2026-03-27 - Fase 4 Lote 1 (Pipeline Canonica de Features)

### DECISION
Consolidar os entrypoints operacionais de treino e calibracao para usar FeatureStore como fonte canonica de geracao de features, removendo o acoplamento direto a features_v2 nesses fluxos.

### CONTEXT
A inferencia principal ja usa FeatureStore, mas fluxos de treino e calibracao ainda chamavam create_advanced_features diretamente em modulos operacionais.

### CHANGES
- Fluxos operacionais migrados para FeatureStore.get_training_features:
  - src/training/trainer.py
  - scripts/train_model.py
  - src/scripts/save_production_calibrator.py
  - src/ml/calibration.py (train_calibrator_from_history)
- Contratos de fase reforcados:
  - tests/contract/test_feature_pipeline_contract.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_feature_pipeline_contract.py tests/test_feature_store.py -q
- python -m pytest tests -q

Resultado:
- 60 passed

### RISK
- Modulos de pesquisa/analise continuam importando create_advanced_features diretamente (escopo fora do fluxo operacional desta etapa).
- PerformanceWarning em features_v2 permanece (debt conhecido, sem regressao funcional).

### NEXT STEP
Fase 4 Lote 2: reduzir caminhos paralelos remanescentes em modulos de treino/analise avancada e definir fronteira explicita entre pipeline operacional e research.

## 2026-03-27 - Fase 4 Lote 2 (Consolidacao Operacional Adicional)

### DECISION
Expandir a consolidacao canonica para o treino do NeuralChallenger e para o wrapper legado de model_v2, garantindo que ambos usem FeatureStore.get_training_features.

### CONTEXT
Mesmo apos o Lote 1, ainda havia caminho operacional de treino neural e helper legado de modelo chamando features_v2 diretamente.

### CHANGES
- Treino neural migrado para FeatureStore:
  - src/ml/train_neural.py
- Wrapper legado de features em model_v2 migrado para FeatureStore:
  - src/models/model_v2.py (prepare_improved_features)
- Contratos de fase ampliados:
  - tests/contract/test_feature_pipeline_contract.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_feature_pipeline_contract.py tests/test_feature_store.py -q
- python -m pytest tests -q

Resultado:
- 61 passed

### RISK
- Modulos de analise/research e web legado ainda usam create_advanced_features diretamente.
- Warning de fragmentacao em features_v2 segue como debito de performance conhecido.

### NEXT STEP
Fase 4 Lote 3: classificar e isolar modulos fora de producao (research/legacy), com politica KEEP/MOVE/LEGACY/DELETE explicitada por arquivo.

## 2026-03-27 - Fase 4 Lote 3 (Fronteira Operacional x Research/Legacy)

### DECISION
Estabelecer fronteira explicita por contrato entre runtime operacional e modulos classificados como research/legacy, evitando reacoplamento acidental em producao.

### CONTEXT
A classificacao de destino havia sido definida, mas sem guardrail automatizado para impedir import indevido desses modulos no caminho operacional.

### CHANGES
- Marcacao explicita de classificacao nos modulos fora de producao:
  - src/analysis/drift_check.py (MOVE TO RESEARCH)
  - src/analysis/stationarity.py (MOVE TO RESEARCH)
  - src/scripts/backtest_model.py (MOVE TO RESEARCH)
  - src/scripts/audit_stationarity.py (MOVE TO RESEARCH)
  - src/scripts/audit_calibration_ece.py (MOVE TO RESEARCH)
  - src/web/server.py (MOVE TO LEGACY)
  - src/web/scanner_manager.py (MOVE TO LEGACY)
- Novo contrato de fronteira de runtime:
  - tests/contract/test_runtime_boundaries_contract.py

### TEST EVIDENCE
Comandos executados:
- python -m pytest tests/contract/test_runtime_boundaries_contract.py tests/contract/test_feature_pipeline_contract.py -q
- python -m pytest tests -q

Resultado:
- 63 passed

### RISK
- A fronteira atual previne import textual em entrypoints operacionais principais; nao substitui governanca de empacotamento/deploy.
- Warnings de performance em features_v2 seguem como debito conhecido.

### NEXT STEP
Encerrar Fase 4 e iniciar Fase 5 com foco em registry/formalizacao champion-challenger e controles de promocao.
