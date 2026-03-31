# Plano de Migração por Fases
> Branch: `refactor/multimercado-cientifico` | Data: 2026-03-31

---

## Princípio de Migração

**BROWNFIELD**: nenhum módulo existente é deletado neste branch. Novos módulos são adicionados em paralelo. A troca de comportamento no `ManagerAI` é feita via feature flag (`CHAMPION_ONLY_MODE`), permitindo rollback a qualquer momento.

---

## Fase 1 — Limpeza do Output (Champion-Only)

**Objetivo**: Garantir que o output de produção venha exclusivamente do champion.  
**Risco**: Baixo — apenas desliga o blend; challenger continua calculando em background.

### Arquivos a Modificar

#### `src/analysis/manager_ai.py`
- Adicionar `CHAMPION_ONLY_MODE = True` (feature flag via env var)
- Quando `True`: `final_conf = champion_conf` (não blend)
- Challenger continua sendo executado e logado, mas **não entra no output**

#### `src/domain/models.py`
- Adicionar `MarketOutput` dataclass (novo campo, não quebra existente)
- Manter `PredictionResult` intacto (backward compat)

### Critério de Conclusão da Fase 1
- [ ] `ManagerAI.predict_match()` com `CHAMPION_ONLY_MODE=True` não usa `neural_raw` no output
- [ ] Shadow log do challenger salvo em banco (tabela `shadow_predictions`)
- [ ] Testes de regressão em `tests/unit/test_manager_ai_champion_only.py`

---

## Fase 2 — Scaffold do Vetor Latente e MarketTranslator

**Objetivo**: Criar a infraestrutura para o modelo joint sem impactar produção.  
**Risco**: Nulo para produção — arquivos novos apenas.

### Novos Arquivos

| Arquivo | Conteúdo |
|---|---|
| `src/ml/joint_model.py` | Interface + NB-Bivariado por período |
| `src/ml/market_translator.py` | Projeção Y → 9 mercados |
| `src/ml/per_market_calibrator.py` | 9 calibradores + pooling hierárquico |
| `src/models/neural_multihead.py` | Challenger multi-cabeça 4 outputs |
| `src/training/joint_trainer.py` | Treino conjunto [h1H,a1H,h2H,a2H] |

### Modificações em Arquivos Existentes

#### `src/ml/features_v2.py`
- Adicionar `create_joint_targets()` — retorna 4 targets em vez de 1
- Sem remover `create_advanced_features()` existente

#### `src/features/feature_store.py`
- Adicionar `get_joint_training_features()` — retorna X, Y_joint (4 colunas)
- Manter `get_training_features()` existente intacto

### Critério de Conclusão da Fase 2
- [ ] `JointPoissonModel.fit(X, Y_joint)` converge sem erro
- [ ] `MarketTranslator.translate(lambda_vector)` retorna 9 keys
- [ ] `PerMarketCalibrator.fit()` accceita cada família separadamente
- [ ] Coerência verificada: `P(ht_total) + P(ht2_total)` ≠ `P(ft_total)` (são mercados separados, não probabilidades somáveis — veriificar que os lambdas somam corretamente)

---

## Fase 3 — Validação Científica (Walk-Forward)

**Objetivo**: Medir o desempenho real dos modelos com protocolo científico.  
**Risco**: Nulo para produção — apenas avaliação offline.

### Novos Arquivos

| Arquivo | Conteúdo |
|---|---|
| `src/training/walk_forward_validator.py` | Rolling temporal split |
| `src/evaluation/__init__.py` | Pacote de avaliação |
| `src/evaluation/sci_evaluator.py` | Brier, LogLoss, RPS, ECE |
| `src/evaluation/ablation_report.py` | Ablação de heurísticas |
| `src/evaluation/market_scorer.py` | Scoring por família de mercado |

### Protocolo de Walk-Forward

```
Dados temporais ordenados:
│←────── treino inicial (60%) ──────→│←── validação (20%) ──→│←── test (20%) ──→│

Rolling windows:
  Fold 1: [0:60%] → avalia [60%:65%]
  Fold 2: [0:65%] → avalia [65%:70%]
  ...
  Fold k: [0:95%] → avalia [95%:100%]

Avaliação por:
  - Liga (ID e nome)
  - Temporada (ano)
  - Família de mercado (9 famílias)
```

### Critério de Conclusão da Fase 3
- [ ] `WalkForwardValidator.run()` produz relatório por fold + por liga
- [ ] ECE medido para todos os 9 mercados derivados
- [ ] Relatório de ablação: winsorização ON vs OFF, blend vs champion-only
- [ ] Resultados salvos em `data/evaluation/` com timestamp

---

## Fase 4 — Treinamento do Vetor Latente (Joint Model)

**Objetivo**: Treinar o modelo joint em produção; comparar com champion atual.  
**Risco**: Médio — requer dados suficientes para 4 targets.

### Pré-requisitos
- [ ] Fase 2 concluída
- [ ] Fase 3 concluída (baseline do champion atual documentado)
- [ ] BD tem ≥ 1.000 partidas com `corners_home_ht` preenchido

### Processo
1. `joint_trainer.py` treina `JointPoissonModel` com walk-forward
2. Resultados comparados contra champion atual (Fase 3)
3. `PerMarketCalibrator` ajustado com out-of-fold predictions
4. Se ECE por família ≤ champion em todas as 9 famílias → candidato a champion

### Critério de Conclusão da Fase 4
- [ ] `JointPoissonModel` treinado e versionado no `ModelRegistry`
- [ ] ECE por família documentado vs. champion atual
- [ ] Relatório de Brier/LogLoss/RPS por família disponível

---

## Fase 5 — Integração no Pipeline de Produção

**Objetivo**: Conectar o joint model ao `ManagerAI` como novo champion.  
**Risco**: Alto — requer testes completos antes.

### Modificações

#### `src/analysis/manager_ai.py`
- `predict_match()` usa `JointPoissonModel` como champion
- Output inclui 9 mercados via `MarketOutput` dataclass
- Challenger neural multi-head continua em shadow

#### `src/domain/strategies/selection_strategy.py`
- Substituir `rank_score = consensus_confidence` por ranking baseado em:
  - `prob_calibrated` × `stability_score`
- Remover Easy/Medium/Hard como categorias de output

#### `src/analysis/unified_scanner.py`
- Substituir Top 7 por output ranqueado completo com metadados de calibração

### Critério de Conclusão da Fase 5
- [ ] Todos os 9 mercados disponíveis no output com prob_calibrada + ECE local
- [ ] Easy/Medium/Hard não aparecem no output de produção
- [ ] Top N fixo removido; usuário recebe ranking completo
- [ ] Testes de integração passando

---

## Fase 6 — Documentação de Governança e Auditoria

**Objetivo**: Documentar processo de promoção e configurar auditoria contínua.

### Entregáveis
- `docs/governance.md` — política de promoção atualizada
- `src/evaluation/ablation_report.py` — relatório periódico automatizado
- `data/evaluation/` — histórico de métricas por fold + data

---

## Resumo de Fases

| Fase | Escopo | Risco | Branch Status |
|---|---|---|---|
| 1 | Champion-only output (feature flag) | Baixo | Implementar agora |
| 2 | Scaffold joint model + market translator | Nulo | Implementar agora |
| 3 | Walk-forward + avaliação científica | Nulo | Implementar agora |
| 4 | Treino do joint model | Médio | Próxima sprint |
| 5 | Integração produção | Alto | Requer Fases 2+3+4 |
| 6 | Governança + auditoria | Baixo | Paralelo com Fase 3 |
