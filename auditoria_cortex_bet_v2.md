# 🔬 Auditoria Técnica Completa — Cortex Bet
### Revisão por Auditor Especialista: ML Aplicado a Apostas Esportivas
---

## 1. Visão Geral da Arquitetura

O projeto segue uma arquitetura em camadas com os seguintes componentes principais:

```
src/
├── analysis/       # Orquestra a análise, lógica de negócio, motor estatístico
│   ├── manager_ai.py          # Orquestrador central (Pipeline principal)
│   ├── statistical.py         # Motor Poisson/NegBinom + Monte Carlo
│   ├── drift_check.py         # Detecção de concept drift
│   ├── stationarity.py        # Teste ADF por feature
│   ├── unified_scanner.py     # Scanner ao vivo (interface externa)
│   ├── performance_calculator.py
│   └── bet_validator.py / bet_resolver.py / prediction_validator.py
├── ml/             # Engenharia de features e treinamento da rede neural
│   ├── features_v2.py         # Pipeline de features (canal único)
│   ├── train_neural.py        # Treinamento do MLP (Optuna)
│   ├── calibration.py         # Platt / Isotonic / Temperature Scaling
│   └── focal_calibration.py  # Temperature Scaling avançada
├── models/         # Modelos preditivos
│   ├── model_v2.py            # Ensemble GBDT (LightGBM + XGBoost + CatBoost)
│   ├── neural_engine.py       # NeuralChallenger (wrapper do MLP)
│   └── base_predictor.py      # Interface abstrata (ABC)
├── features/       # Infraestrutura de features (inference)
│   └── feature_store.py       # Facade para servir features em treino e inferência
├── database/       # Persistência SQLite
│   ├── db_manager.py          # Acesso legado a dados (~1800 linhas)
│   ├── match_repository.py    # CRUD especializado em partidas
│   ├── prediction_repository.py
│   └── user_repository.py
└── scrapers/
    └── sofascore.py           # Coleta de dados via API SofaScore
```

**Avaliação geral:** Estrutura bem intencionada, mas com camadas duplicadas ([db_manager.py](file:///c:/Users/Valmont/Desktop/Cortex_Bet/src/database/db_manager.py) vs repositórios dedicados) e resíduos de versões anteriores.

---

## 2. Problemas Encontrados (Listados por Gravidade)

### 🔴 Críticos / P0 (Já corrigidos em sessões anteriores)
- P0-A: Focal Weighting inconsistente entre treino e validação → resolvido
- P0-B: Mercado `2º TEMPO (FT)` usava dados do 1° tempo → removido
- P0-C: StandardScaler ajustado no dataset completo antes do split → corrigido

### 🟡 Altos / P1 (Já corrigidos em sessões anteriores)
- P1-A: Divisor do RPS incorreto (N em vez de N-1) → corrigido
- P1-B: `entropy_corners = 0.5` hardcoded → removido
- P1-C: `last_result` com proxy `goals > 1` → corrigido
- P1-D: `is_unbalance + scale_pos_weight` mutuamente excludentes → removidos
- P1-E: Split MLP sem ordenação temporal → corrigido
- P1-F: Blend 60/40 hardcoded → substituído por blend dinâmico

### 🟠 Novos Problemas Identificados nesta Auditoria

| # | Problema | Arquivo | Gravidade |
|---|----------|---------|-----------|
| N1 | Dead code block: `if sample_weights is not None` com `sample_weights = None` sempre | `model_v2.py:391-396` | Médio |
| N2 | `cols_metrics` ainda referência `momentum_home` na linha 103 | `features_v2.py:103` | Baixo |
| N3 | Inúmeros `[DEBUG PREDICT]` prints em produção | `model_v2.py:536-590` | Médio |
| N4 | MLP otimizado somente com MAE — falha distribuicional | `train_neural.py:69,153` | Alto |
| N5 | [calculate_entropy()](file:///c:/Users/Valmont/Desktop/Cortex_Bet/src/ml/features_v2.py#33-69) definida mas nunca chamada em runtime | `features_v2.py:33` | Baixo |
| N6 | [exponential_decay_weight()](file:///c:/Users/Valmont/Desktop/Cortex_Bet/src/ml/features_v2.py#12-31) definida mas não utilizada (obsoleta) | `features_v2.py:12` | Baixo |
| N7 | Dois módulos de calibração: [calibration.py](file:///c:/Users/Valmont/Desktop/Cortex_Bet/src/ml/calibration.py) e [focal_calibration.py](file:///c:/Users/Valmont/Desktop/Cortex_Bet/src/ml/focal_calibration.py) | `src/ml/` | Médio |
| N8 | `db_manager.py` (~1800 linhas) sobrepõe responsabilidades de `match_repository.py` | `database/` | Médio |
| N9 | `predict_lambda()` do ProfessionalPredictor divide total 50/50 sem base estatística | `model_v2.py:500-509` | Alto |
| N10 | Feature Store adiciona display metrics ao vetor de input → possível poluição | `feature_store.py:136-137` | Médio |
| N11 | `_generate_synthetic_odds()` tem bug: `naive_pred` é calculado duas vezes | `model_v2.py:262-266` | Baixo |
| N12 | `unified_scanner.py` injeta `odds=1.90` como placeholder | `unified_scanner.py:117,311` | Médio |

---

## 3. Código Redundante ou Obsoleto

### 3.1 Funções Definidas mas Nunca Chamadas
```python
# features_v2.py
def exponential_decay_weight(...)  # Linha 12 — Não há chamada em nenhum arquivo
def calculate_entropy(...)          # Linha 33 — Definida mas comentada na linha de uso

# calibration.py
class CalibratedConfidence         # Carregada? manager_ai.py usa MultiThresholdCalibrator
class MultiThresholdCalibrator     # Apenas carregada em calibration.py, integração incompleta
```

### 3.2 Dead Code no Loop de Treinamento
```python
# model_v2.py — linhas 391-396 (nunca executadas)
if sample_weights is not None:
    self.model.fit(X_train, y_train, sample_weight=sample_weights)
else:
    # SEMPRE entra aqui, pois sample_weights = None na linha 386
    self.model.fit(X_train, y_train)
```

### 3.3 Duplicação de Calibração
Existem **dois módulos distintos de calibração** com funcionalidades sobrepostas:
- `calibration.py` → `CalibratedConfidence`, `MultiThresholdCalibrator`
- `focal_calibration.py` → `TemperatureScaling`, `FocalCalibrationWrapper`

`manager_ai.py` tenta carregar `MultiThresholdCalibrator` mas o arquivo `data/calibrator_temperature.pkl` frequentemente não é encontrado, fazendo o sistema operar sem calibração real.

### 3.4 Scripts Raiz Desnecessários
Na raiz do projeto:
- `debug_import.py`, `dump_error.py`, `inspect_db.py`, `mass_replace.py` — scripts de debug soltos
- `debug_matches.py`, `test_dynamic_lines.py` — testes ad-hoc sem registro no pytest

---

## 4. Problemas Estatísticos ou de Modelagem

### 4.1 Problema da Independência Condicional dos Escanteios

**Suporte científico:** Dixon & Coles (1997) demonstraram que gols de mandante e visitante não são condicionalmente independentes. O mesmo vale para escanteios (Karlis & Ntzoufras, 2009).

O projeto usa modelagem **independente** de λ_home e λ_away, com somatório `lambda_total = l_home + l_away`. Isso ignora a correlação negativa entre os escanteios dos dois times (mandante que domina tende a ter mais escanteios *e* o visitante tende a ter menos). Uma abordagem bivariada (Bivariate Poisson) capturaria isso.

### 4.2 Suposição de Equidispersão (Poisson) vs Overdispersão (NegBinom)

**Suporte científico:** Sobre dados de escanteios, Bitteur & Forest (2016) confirmam overdispersão sistemática (variância > média em ~80% dos jogos). O projeto detecta overdispersão em tempo de inferência (`sigma2 > mu`), mas durante o treinamento do GBDT o objetivo `tweedie` simula equidispersão por padrão (variance_power=1.5). Isso causa inconsistência entre regime de treino e inferência.

### 4.3 Avaliação de RPS com Distribuição Poisson Truncada

A implementação do RPS usa `max_outcomes = 25`. Segundo Epstein (1969), a escolha do número de categorias afeta o RPS. Para escanteios (que podem chegar a 20+), o limite de 25 é adequado. **Aprovado.**

### 4.4 Monte Carlo com 10.000 Simulações

O número de simulações está em `self.n_simulations = 10000` em `statistical.py`. Para probabilidades de eventos com p ≥ 0.01, o erro padrão de Monte Carlo é σ ≈ √(p(1-p)/N) ≈ 0.003. **Aprovado para uso prático.**

### 4.5 Blend Dinâmico MLP + Estatístico

A nova fórmula:
```python
neural_weight = 0.5 + (0.35 * (mu / max(sigma2, mu)))
```
Quando `mu = sigma2` (equidispersão), peso neural = 0.85. Problema: `mu` é o λ esperado (contagem), não uma probabilidade. A fórmula deveria ser baseada em **Brier Score** ou **Reliability Diagram** calibrado, não em sigma2/mu (que é o índice de dispersão, não de confiança do modelo).

**Recomendação:** Usar uma pool de ensembles com combinação por minimização do Brier Score out-of-sample (Gneiting & Raftery, 2007).

---

## 5. Problemas de Machine Learning

### 5.1 MLP Avaliado por MAE — Inadequado para Contagens

O objetivo de otimização do Optuna é o **MAE médio** entre escanteios do mandante e visitante:
```python
mae = (mae_home + mae_away) / 2
```

📖 **Problema científico:** MAE penaliza erros de forma simétrica e linear, mas não captura qualidade probabilística. Para contagens esportivas, a literatura recomenda:
- **Poisson Deviance** (Gneiting & Raftery, 2007)
- **Log-Likelihood de Poisson Bivariada** (Karlis & Ntzoufras, 2009)
- **Continuous Ranked Probability Score (CRPS)** — análogo do RPS para distribuições contínuas

### 5.2 MLP de Camada Rasa com Inputs Altamente Redundantes

O MLP busca entre 1-3 camadas com 16-128 neurônios sobre ~120 features de alta correlação (EMA_3g, EMA_5g, EMA_10g são colineares). Isso tende a:
- Superajustar os dados de treino
- Convergir para funções de plateau (R² ≈ 0 observado no output dos logs)

📖 **Suporte científico:** Kovalchik & Albert (2022) demonstraram que redes neurais rasas com inputs de alta correlação em dados esportivos frequentemente não superam modelos lineares simples.

### 5.3 Stacking com TimeSeriesSplit Interno + Externo

O treinamento usa dois níveis de TimeSeriesSplit:
- **Externo** (n_splits=5): Para métricas de validação
- **Interno** (n_splits=3): Dentro do `TimeAwareStacking.fit()` para gerar meta-features

Isso pode originar **data leakage no conjunto OOF**: os mesmos dados de validação externa participam da geração de meta-features no split interno. Recomenda-se garantir que os folds internos sempre sejam subconjuntos dos folds de treino externos.

### 5.4 Ridge como Meta-Learner sem Restrição de Não-Negatividade

O Ridge linear (α=1.0) como meta-learner pode aprender pesos negativos para os base learners. Como todos os modelos base preveem contagens positivas (escanteios), um peso negativo não tem interpretação física.

📖 **Alternativa:** `LinearRegression` com `positive=True` (scikit-learn) ou `Lasso` com regularização.

### 5.5 Optuna Otimizando no Conjunto de Teste

```python
study.optimize(lambda trial: objective(trial, X_train, y_train, X_test, y_test), n_trials=n_trials)
```

O Optuna **usa X_test para seleção de hiperparâmetros**. Isso viola a separação treino/validação/teste. O conjunto de teste deve ser usado apenas para avaliação final após seleção de hiperparâmetros.

📖 **Protocolo correto:** Usar `X_train` para treino e um subconjunto de validação *separado* para seleção de hiperparâmetros, ou usar cross-validation interna dentro do objetivo Optuna.

---

## 6. Problemas de Engenharia de Dados

### 6.1 Feature Store vs features_v2 — Duplicação de Responsabilidade

`feature_store.py` delega para `create_advanced_features()` em `features_v2.py`. Ambos os arquivos existem, mas `features_v2.py` é **invocado diretamente** em `train_neural.py` e `stationarity.py`, bypassando o Feature Store. Isso quebra o contrato de "Single Source of Truth".

### 6.2 Winsorização Unilateral e Valor Arbitrário

```python
relevant_games["corners_home_ft"].clip(lower=3.0)
```

O limite de `3.0` é arbitrário. Jogos com 0-2 escanteios são raros mas existem e não podem ser descartados ou modificados sem justificativa estatística. A winsorização deve ser validada pelo percentil 1% ou 5% dos dados históricos.

### 6.3 Stationarity Check Incompleto

O teste ADF verifica estacionariedade marginal de cada feature individualmente. Features multicollineares podem ser estacionárias marginalmente mas não conjuntamente (cointegração). Para um modelo de ensemble GBDT, isso é menos crítico, mas para o MLP é relevante.

### 6.4 Vazamento de Display Metrics no Vetor de Features

```python
# feature_store.py:136-137
for col in display_single.columns:
    features_single[col] = display_single[col].values[0]
```

Display metrics (como `home_avg_corners_general`, `home_avg_dangerous_attacks_general`) são **concatenadas ao dataframe de features retornado pelo FeatureStore**. O modelo que recebe esse dataframe vê mais colunas do que foi treinado. A `predict()` do ProfessionalPredictor filtra por `self.feature_names`, o que salva de erros imediatos, mas é uma redundância perigosa — se alguém usar o vetor sem filtragem, o modelo quebrará silenciosamente.

---

## 7. Recomendações de Melhoria (Baseadas em Literatura)

### Alta Prioridade

| Recomendação | Justificativa Científica | Referência |
|---|---|---|
| Substituir Optuna com validação interna (não no test set) | Previne selection bias | Bergstra & Bengio (2012) |
| Avaliar MLP por Poisson Log-Likelihood ou CRPS, não MAE | MAE não mede qualidade probabilística | Gneiting & Raftery (2007) |
| Implementar Bivariate Poisson para correlação Home/Away | Independência condicional violada em futebol | Karlis & Ntzoufras (2009) |
| Consolidar os dois módulos de calibração em um único | Single Responsibility Principle | — |

### Média Prioridade

| Recomendação | Justificativa Científica | Referência |
|---|---|---|
| Remover prints DEBUG de produção | Degradação de performance em sistemas live | — |
| Eliminar dead code: `if sample_weights is not None: ...` | Código morto aumenta custo de manutenção | — |
| Usar `positive=True` no Ridge meta-learner | Pesos negativos sem interpretação física | — |
| Implementar teste KPSS junto ao ADF para diagnóstico completo | ADF tem baixo poder em amostras pequenas | Kwiatkowski et al. (1992) |
| Blend por Brier Score calibrado no lugar de sigma2/mu | O índice de dispersão não mede confiança do modelo | Gneiting & Raftery (2007) |

### Baixa Prioridade

| Recomendação | Justificativa Científica |
|---|---|
| Remover `calculate_entropy()` e `exponential_decay_weight()` não utilizadas | Higiene de código |
| Remover referência `momentum_home` em `cols_metrics` | Inconsistência com refactoring anterior |
| Eliminar scripts raiz de debug (`dump_error.py`, `inspect_db.py`) | Ruído no repositório |
| Unificar db_manager.py e match_repository.py | Responsabilidade única (SRP) |

---

## 8. Sugestão de Arquitetura Ideal (Literatura Científica)

```
Arquitetura Ideal para Previsão de Escanteios
(baseada em Dixon & Coles 1997, Karlis & Ntzoufras 2009, Maher 1982)

                        ┌─────────────────────────────────┐
                        │         DADOS HISTÓRICOS         │
                        │   (DB + Scraping em tempo real)  │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │    FEATURE STORE (Único)         │
                        │  - Team-centric EMAs             │
                        │  - H2H, SoS, SoD                 │
                        │  - Rest days                     │
                        └──────────────┬──────────────────┘
                                       │
              ┌────────────────────────▼────────────────────────┐
              │              CAMADA DE MODELOS                    │
              │  ┌─────────────────┐  ┌────────────────────────┐│
              │  │  GBDT Ensemble  │  │ Bivariate Poisson MLE  ││
              │  │  (LightGBM +    │  │  (Dixon-Coles style)   ││
              │  │   XGBoost +     │  │  λ_home, λ_away        ││
              │  │   CatBoost)     │  │  correlação ρ          ││
              │  │  Objetivo:      │  │  Karlis-Ntzoufras (09) ││
              │  │  Poisson Dev.   │  └────────────────────────┘│
              │  └─────────────────┘                            │
              └────────────────────┬────────────────────────────┘
                                   │
              ┌────────────────────▼────────────────────────────┐
              │         ENSEMBLE COM PESOS POR BRIER SCORE       │
              │         (calibrado no conjunto holdout)           │
              │         Gneiting & Raftery (2007)                │
              └────────────────────┬────────────────────────────┘
                                   │
              ┌────────────────────▼────────────────────────────┐
              │         CALIBRAÇÃO PÓS-HOC                       │
              │  Temperature Scaling (Guo et al., 2017)          │
              └────────────────────┬────────────────────────────┘
                                   │
              ┌────────────────────▼────────────────────────────┐
              │         MOTOR DE MERCADOS                         │
              │  P(Over/Under k) via CDF bivariada               │
              │  EV = P_modelo × Odd_casa – (1 – P_modelo)       │
              └─────────────────────────────────────────────────┘
```

---

## 9. Referências Científicas Utilizadas

| Referência | Relevância no Projeto |
|---|---|
| Dixon & Coles (1997). *Modelling Association Football Scores*. Applied Statistics. | Base para modelagem bivariada λ_home/λ_away |
| Karlis & Ntzoufras (2009). *Bayesian modelling of football outcomes*. IMA J. Manag. Math. | Bivariate Poisson para correlação entre times |
| Maher (1982). *Modelling association football scores*. Statistica Neerlandica. | Modelo base de ataque/defesa por time |
| Epstein (1969). *A Scoring System for Probability Forecasts*. BAMS. | Fórmula correta do RPS |
| Gneiting & Raftery (2007). *Strictly Proper Scoring Rules, Prediction & Estimation*. JASA. | CRPS, Brier Score, regras de scoring próprias |
| Guo et al. (2017). *On Calibration of Modern Neural Networks*. ICML. | Temperature Scaling |
| Platt (1999). *Probabilistic Outputs for Support Vector Machines*. | Platt Scaling |
| Niculescu-Mizil & Caruana (2005). *Predicting Good Probabilities with Supervised Learning*. ICML. | Comparação Platt vs Isotonic |
| Bergstra & Bengio (2012). *Random Search for Hyper-Parameter Optimization*. JMLR. | Protocolo de HPO |
| Chen & Guestrin (2016). *XGBoost*. KDD. | Modelo XGBoost |
| Prokhorenkova et al. (2018). *CatBoost: unbiased boosting with categorical features*. NeurIPS. | CatBoost |
| Kwiatkowski et al. (1992). *Testing the null hypothesis of stationarity*. Journal of Econometrics. | Teste KPSS |
| Spyromitros-Xioufis et al. (2016). *Multi-Target Regression via Input Space Expansion*. ECML. | Multi-output MLP |
| Kovalchik & Albert (2022). *A statistical model of player performance in the NBA*. — | Limitações de redes neurais em dados esportivos |

---

## 10. Modularização: Arquivos Obsoletos ou Não Utilizados

### ❌ Eliminação Recomendada (sem impacto em produção)

| Arquivo | Razão |
|---|---|
| `debug_import.py` (raiz) | Script de debug solto |
| `dump_error.py` (raiz) | Script de debug solto |
| `inspect_db.py` (raiz) | Script de debug solto |
| `mass_replace.py` (raiz) | Script de refactoring pontual |
| `debug_matches.py` (raiz) | Teste ad-hoc |
| `test_dynamic_lines.py` (raiz) | Teste sem registro no pytest |
| `error.txt` (raiz) | Arquivo de log manual |
| `out.txt` (raiz) | Arquivo de output manual |
| `scrapers/manual_previsao_escanteios.txt` | Documento de rascunho manual |

### ⚠️ Consolidação Recomendada

| Arquivo | Ação |
|---|---|
| `calibration.py` + `focal_calibration.py` | Mesclar em `calibration.py` único |
| `db_manager.py` (1800 linhas) + repositórios | Refatorar: legado → use match_repository exclusivamente |

### ✅ Módulos em Bom Estado

| Arquivo | Status |
|---|---|
| `base_predictor.py` | Interface bem definida, mantida |
| `feature_store.py` | Façade limpa, arquitetura sólida |
| `stationarity.py` | Uso correto do ADF |
| `drift_check.py` | PSI implementado recentemente |
| `unified_scanner.py` | Funcional mas com placeholder de odds |
