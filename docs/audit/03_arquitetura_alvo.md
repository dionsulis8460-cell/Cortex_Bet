# Arquitetura-Alvo Multimercado
> Branch: `refactor/multimercado-cientifico` | Data: 2026-03-31

---

## 1. Princípio Central

O sistema modela **explicitamente** a distribuição conjunta do vetor latente:

$$\mathbf{Y} = [\text{home\_1H},\ \text{away\_1H},\ \text{home\_2H},\ \text{away\_2H}]$$

Todos os 9 mercados derivados são projeções desta distribuição base — nunca calculados independentemente.

### Restrições de Coerência Obrigatórias

$$\text{home\_ft} = \text{home\_1H} + \text{home\_2H}$$
$$\text{away\_ft} = \text{away\_1H} + \text{away\_2H}$$
$$\text{total\_ft} = \text{home\_ft} + \text{away\_ft}$$
$$\text{total\_1H} = \text{home\_1H} + \text{away\_1H}$$
$$\text{total\_2H} = \text{home\_2H} + \text{away\_2H}$$

---

## 2. Diagrama de Fluxo da Arquitetura-Alvo

```
┌───────────────────────────────────────────────────────┐
│                    FeatureStore                        │
│   (única fonte de truth — treino e inferência)         │
└──────────────────────┬────────────────────────────────┘
                       │  X: features
              ┌────────┴─────────┐
              │                  │
    ┌─────────▼──────┐  ┌────────▼──────────────┐
    │ CHAMPION        │  │ CHALLENGER (shadow)    │
    │ JointPoissonMdl │  │ NeuralMultiHead        │
    │ (Bivariado NB   │  │ (MLP/4 cabeças)        │
    │  4 componentes) │  │                        │
    └─────────┬──────┘  └────────┬───────────────┘
              │  λ=[h1H,a1H,     │  λ=[h1H,a1H,
              │    h2H,a2H]      │    h2H,a2H]
              │                  │ (não entra no output)
              └────────┬─────────┘
                       │ apenas champion output
         ┌─────────────▼──────────────────────────┐
         │           MarketTranslator              │
         │   Projeta Y → 9 mercados derivados      │
         │   (via distribuição marginal analítica  │
         │    ou Monte Carlo calibrado)             │
         └─────────────┬──────────────────────────┘
                       │ P(market_i | Y)
         ┌─────────────▼──────────────────────────┐
         │        PerMarketCalibrator              │
         │   9 calibradores independentes          │
         │   (Isotonic + pooling hierárquico)      │
         └─────────────┬──────────────────────────┘
                       │ calibrated P per market
         ┌─────────────▼──────────────────────────┐
         │          MultiMarketOutput              │
         │   Ranqueio por: P_calibrada,            │
         │   estabilidade por liga, ECE local      │
         │   (sem Easy/Medium/Hard, sem Top N fixo)│
         └─────────────────────────────────────────┘
```

---

## 3. Champion — Modelo de Contagem Bivariado

### 3.1 Fatoração do Vetor Latente

Abordagem recomendada: **fatoração temporal 1H/2H + dependência home/away**.

#### Opção A — Negative Binomial Bivariado (NB-Biv) por período
Modela dois pares independentes:
- $(X_{1H}, Y_{1H})$ — Bivariate Poisson/NB com $\lambda_3^{1H}$
- $(X_{2H}, Y_{2H})$ — Bivariate Poisson/NB com $\lambda_3^{2H}$

As marginais FT são somas: $X_{FT} = X_{1H} + X_{2H}$ (coerência garantida).

#### Opção B — Multinomial Copula (Poisson marginals + Gaussian copula)
Modela $\mathbf{Y}$ diretamente com correlação entre 4 componentes via cópula.

**Recomendação inicial**: Opção A (NB-Biv por período) — mais interpretável, mais fácil de calibrar por família.

### 3.2 Parâmetros a Estimar (por jogo)

$$\boldsymbol{\lambda} = [\lambda_{h1H},\ \lambda_{a1H},\ \lambda_{h2H},\ \lambda_{a2H},\ \lambda_3^{1H},\ \lambda_3^{2H}]$$

Onde $\lambda_3^{period}$ é o termo de covariância (choque comum) por período.

### 3.3 Covariates (Features → Parâmetros)

O modelo usa o `FeatureStore` para mapear features → $\boldsymbol{\lambda}$.
Arquitetura sugerida: **LGBM multi-output** ou **4 regressores independentes com meta-learner conjunto**.

---

## 4. Challenger — Neural Multi-Head (Shadow Mode)

### 4.1 Arquitetura

```python
# Neural Multi-Head — 4 cabeças de saída
class NeuralMultiHead(nn.Module):
    def __init__(self):
        self.trunk = MLP(input_dim, hidden=[256, 128])  # shared
        self.head_h1h = LinearPositive(128, 1)   # λ_home_1H
        self.head_a1h = LinearPositive(128, 1)   # λ_away_1H
        self.head_h2h = LinearPositive(128, 1)   # λ_home_2H
        self.head_a2h = LinearPositive(128, 1)   # λ_away_2H
```

Output: vetor $[\hat\lambda_{h1H},\ \hat\lambda_{a1H},\ \hat\lambda_{h2H},\ \hat\lambda_{a2H}]$

O challenger **nunca aparece no output** para o usuário. Seus logs ficam em database/shadow_log.

### 4.2 Critérios de Promoção (Ampliados)

O challenger só pode ser promovido se:
1. Brier score global melhora ≥ 3% em walk-forward reproduzível
2. Log-loss global melhora ≥ 3%
3. ECE por família ≤ ECE do champion em TODAS as 9 famílias
4. Nenhuma família (1T, 2T, por time) tem degradação > 5% vs champion
5. Avaliado em ≥ 150 partidas de holdout

---

## 5. MarketTranslator — Projeção da Distribuição

```python
class MarketTranslator:
    """
    Projeta Y = [home_1H, away_1H, home_2H, away_2H] em 9 mercados.
    
    Pode usar:
    - Forma analítica (convolução de Poisson/NB marginais)
    - Monte Carlo calibrado (N=50.000 simulações, seed fixo por jogo)
    """
    
    MARKET_FAMILIES = [
        'ft_total',       # X_FT = h1H+a1H+h2H+a2H
        'ht_total',       # X_1H = h1H+a1H
        'ht2_total',      # X_2H = h2H+a2H
        'ft_home',        # h1H+h2H
        'ft_away',        # a1H+a2H
        'ht_home',        # h1H
        'ht_away',        # a1H
        'ht2_home',       # h2H
        'ht2_away',       # a2H
    ]
    
    def translate(self, lambda_vector: np.ndarray, method: str = 'montecarlo') -> Dict[str, np.ndarray]:
        """Retorna distribuição simulada para cada família de mercado."""
```

**Monte Carlo calibrado** = a frequência empírica das simulações é comparada contra hold-out histórico (not just used as-is).

---

## 6. PerMarketCalibrator — 9 Calibradores

```python
class PerMarketCalibrator:
    """
    9 calibradores independentes — um por família de mercado.
    
    Quando amostra < 100 jogos por família: pooling hierárquico
    (shrink en direção a calibrador familiar agregado).
    
    Método: Isotonic Regression (non-parametric, monotone).
    Fallback: Temperatura scaling quando amostra < 30 jogos.
    """
    
    FAMILIES = [
        'ft_total', 'ht_total', 'ht2_total',
        'ft_home', 'ft_away',
        'ht_home', 'ht_away', 'ht2_home', 'ht2_away'
    ]
```

---

## 7. MultiMarketOutput — Saída Oficial

### 7.1 Campos por Mercado
```python
@dataclass
class MarketOutput:
    family: str
    line: float
    direction: str          # 'over' | 'under'
    prob_raw: float         # probabilidade bruta do modelo
    prob_calibrated: float  # após PerMarketCalibrator
    uncertainty: float      # std dev via bootstrap ou MC
    brier_score_30d: float  # calibração recente local
    ece_30d: float          # ECE dos últimos 30 dias
    stability_score: float  # estabilidade por liga/temporada
    # NOTE: sem fair_odd como critério de ranking; apenas como info
    fair_odd: float         # 1/prob_calibrated — informativo
    # NOTE: sem ev_percentage; sem kelly; sem easy/medium/hard
```

### 7.2 Ranking Oficial
Ordenado por: `prob_calibrated DESC` com desempate por `stability_score DESC`.

**Proibido como critério primário:**
- fair_odd
- ev_percentage
- kelly
- hit_rate
- Easy/Medium/Hard categorias

### 7.3 Comparação com Odd do Usuário (Opcional)
Quando o usuário informa uma odd manualmente:
```python
def compare_with_user_odd(prob_calibrated: float, user_odd: float) -> Dict:
    fair_odd = 1 / prob_calibrated
    implied_prob = 1 / user_odd
    edge = prob_calibrated - implied_prob
    return {
        'fair_odd': fair_odd,
        'edge_vs_market': edge,
        'interpretation': 'value' if edge > 0 else 'no_value'
    }
```
Isso nunca é exibido sem a odd do usuário informada.

---

## 8. Pipeline de Validação Científica

```
FeatureStore
    ↓
WalkForwardValidator (temporal, rolling, por liga)
    ↓
SciEvaluator
    ├── Brier Score por família
    ├── Log Loss por família
    ├── RPS/CRPS por família
    ├── ECE/Reliability por família
    ├── MAE do valor esperado
    ├── Sharpness
    ├── Cobertura de intervalos
    └── Estabilidade (por liga, por temporada)
    ↓
AblationReport
    ├── Winsorização clip(3.0) vs. sem clip
    ├── Blend champion+challenger vs. apenas champion
    └── Dummy-row assumption (zeros vs. médias)
```

---

## 9. Estrutura de Arquivos da Arquitetura-Alvo

```
src/
  ml/
    joint_model.py          ← NOVO: vetor latente [h1H,a1H,h2H,a2H]
    market_translator.py    ← NOVO: projeção em 9 mercados
    per_market_calibrator.py← NOVO: 9 calibradores + pooling hierárquico
    calibration.py          ← EXISTENTE: manter; depreciado para FT-only
    features_v2.py          ← EXISTENTE: adicionar targets 1H/2H
  models/
    model_v2.py             ← EXISTENTE: manter como fallback FT
    neural_engine.py        ← EXISTENTE: substituir por neural_multihead.py
    neural_multihead.py     ← NOVO: 4 cabeças multi-output
    model_registry.py       ← EXISTENTE: ampliar política de promoção
  training/
    trainer.py              ← EXISTENTE: manter treino FT
    joint_trainer.py        ← NOVO: treino do vetor latente conjunto
    walk_forward_validator.py ← NOVO: validação temporal rolling
  evaluation/
    __init__.py             ← NOVO
    sci_evaluator.py        ← NOVO: métricas primárias e secundárias
    ablation_report.py      ← NOVO: ablação de heurísticas
    market_scorer.py        ← NOVO: scoring por família
  analysis/
    manager_ai.py           ← EXISTENTE: refatorar para champion-only output
    unified_scorer.py       ← NOVO: output multimercado (sem Easy/Medium/Hard)
  domain/
    models.py               ← EXISTENTE: adicionar MarketOutput dataclass
```
