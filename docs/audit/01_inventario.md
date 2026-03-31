# Inventário do Estado Atual — Cortex Bet
> Branch: `refactor/multimercado-cientifico` | Data: 2026-03-31

---

## 1. Mapa de Módulos Relevantes

| Arquivo | Papel | Estado Atual |
|---|---|---|
| `src/models/model_v2.py` | Champion (Ensemble Stacking: LGBM + RF + Linear meta) | Ativo — prediz FT total (Tweedie) |
| `src/models/neural_engine.py` | Challenger (MLPRegressor) | Shadow mode — mas mesclado no output final |
| `src/models/model_registry.py` | Registro champion/challenger | Implementado; promove por Brier/LogLoss |
| `src/features/feature_store.py` | Fonte única de features | Implementado; inclui dummy-row pipeline |
| `src/ml/features_v2.py` | Pipeline de feature engineering | FT corners only; HT é feature, não target |
| `src/ml/calibration.py` | Calibração probabilística | Platt/Isotonic/Temperature — 1 modelo global |
| `src/ml/focal_calibration.py` | Focal weighting para treino | Ativo |
| `src/analysis/manager_ai.py` | Orquestrador de previsões | Mistura champion + challenger no output |
| `src/analysis/statistical.py` | Monte Carlo + Bivariate Poisson | Monte Carlo não calibrado formalmente |
| `src/analysis/unified_scanner.py` | Scanner de jogos | Usa Top 7 como critério heurístico |
| `src/domain/strategies/selection_strategy.py` | Ranking de picks | Rank por confiança bruta (heurístico) |
| `src/analysis/bet_resolver.py` | Resolução de apostas historicas | 2T derivado por `total_ft - total_ht` |
| `src/analysis/bet_validator.py` | Validação de apostas | 2T derivado por `total_ft - total_ht` |
| `src/training/trainer.py` | Pipeline de treino | Treina apenas FT total |
| `src/models/base_predictor.py` | Interface base dos modelos | Define `predict_lambda()` → (home, away) FT |

---

## 2. Estrutura de Features Atual

### 2.1 Target de Treino Atual
Conforme `features_v2.py`, `create_advanced_features()`:
- **Target único**: `corners_home_ft + corners_away_ft` (total de escanteios FT)
- **HT corners**: usados apenas como *feature de input*, nunca como target

### 2.2 Features Geradas
- Médias móveis gerais (rolling 3 e 5 jogos)
- Médias móveis home/away específicas
- Médias de concessão (defensiva)
- H2H (confrontos diretos)
- Trend (curto vs longo prazo)
- Volatilidade (desvio padrão)
- Rest days (fadiga)
- EMA (Exponential Moving Average com decay)
- Força relativa (interações)
- Entropia de Shannon (imprevisibilidade)

### 2.3 Winsorização
- `corners_home_ft.clip(lower=3.0)` e `corners_away_ft.clip(lower=3.0)` em `FeatureStore.build_match_features()`
- **Sem ablação temporal formal** — aplicado sempre

---

## 3. Pipeline de Inferência Atual

```
FeatureStore.build_match_features()
        ↓
ensemble.predict() → lambda_total_ft (champion)
neural.predict_lambda() → (λ_home_ft, λ_away_ft) (challenger)
        ↓
manager_ai._find_best_line()
        ↓
final_conf = (champion_conf * 0.5 + prob_score * 0.5) * agreement
        ↓
statistical.simulate_match_event()  ← Monte Carlo não calibrado
        ↓
PredictionResult (FT Total + mercados HT por histórico separado)
```

**Problema central**: O output final é um blend de champion + challenger — viola a diretriz de 1 champion oficial.

---

## 4. Geração de Mercados HT/2T

### Onde está o problema:
| Local | Código | Tipo de Violação |
|---|---|---|
| `bet_resolver.py:23` | `total_2h = total_ft - total_ht` | Derivação ingênua por diferença |
| `bet_validator.py:122` | `total_2h = total_ft - total_ht` | Idem |
| `statistical.py:589-603` | Lambdas HT calculados do histórico HT separado | Sem vínculo com λ_FT do modelo |
| `neural_engine.py:predict_lambda()` | Retorna `(lambda_home_ft, lambda_away_ft)` | Não há saída de 1H/2H |
| `model_v2.py` | Prediz apenas `y = corners_total_ft` | Sem vetor [home_1H, away_1H, home_2H, away_2H] |

---

## 5. Calibração Atual

| Componente | O que faz | Problema |
|---|---|---|
| `CalibratedConfidence` | Platt/Isotonic/Temperature scaling | Binário Over/Under por 1 limiar global |
| `MultiThresholdCalibrator` | Calibra por múltiplas linhas | FT total apenas |
| `calibrator_temperature.pkl` | Carregado em ManagerAI | Único arquivo para todos os mercados |
| Mercados 1T, 2T, por time | **Sem calibrador próprio** | Calibração assumida, nunca medida |

---

## 6. Critério de Ranking Atual

Da `SelectionStrategy.evaluate_candidates()`:
```python
rank_score = res.consensus_confidence  # confiança bruta
```

Da `generate_suggestions()` em `statistical.py`:
- Easy: `prob >= 0.60 AND FairOdd >= 1.25`
- Medium: `0.50 <= prob < 0.60 AND FairOdd >= 1.25`
- Hard: `0.40 <= prob < 0.50 AND FairOdd >= 1.25`

**Problema**: Easy/Medium/Hard são limiares fixos sem ablação. FairOdd como critério filtra por valor teórico sem odd real de referência.

---

## 7. ModelRegistry — Estado

O `model_registry.json` define:
- 1 champion (`ensemble_v1`)
- 1 challenger (`neural_challenger_v1`)
- Política de promoção: Brier melhora ≥3% E LogLoss melhora ≥3% E ≥150 partidas

**Problema**: Critérios de promoção não incluem calibração por família de mercado nem estabilidade por liga/temporada.

---

## 8. Resumo das Violações das Diretrizes

| Diretriz | Status |
|---|---|
| 1 champion oficial | ❌ champion e challenger mesclados no output |
| 1 challenger em shadow mode puro | ❌ challenger contribui para output final |
| Vetor latente [home_1H, away_1H, home_2H, away_2H] | ❌ não existe |
| 2T por modelo, não por diferença | ❌ `2T = FT - 1T` em bet_resolver/validator |
| Calibradores por família de mercado | ❌ 1 calibrador global para FT total |
| Calibração medida (ECE/reliability) | ❌ calibração assumida |
| Ranking por probabilidade calibrada + estabilidade | ❌ rank por confiança bruta |
| Monte Carlo calibrado | ❌ simulações sem calibração formal |
| Ablação de winsorização | ❌ clip(3.0) sempre ativo |
| Promoção por calibração + por família | ⚠️ só Brier/LogLoss globais |
| Sem Top 7 / Easy/Medium/Hard como critério oficial | ❌ usados em scanner e statistical |
