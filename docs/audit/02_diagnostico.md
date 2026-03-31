# Diagnóstico de Mercados — Válidos e Inválidos
> Branch: `refactor/multimercado-cientifico` | Data: 2026-03-31

---

## 1. Mercados Atualmente Produzidos

| Mercado | Produzido? | Metodologia Atual | Válido Cientificamente? |
|---|---|---|---|
| FT Total (Over/Under) | ✅ Sim | Champion prediz λ_total_ft via Tweedie/Stacking | ⚠️ Parcialmente — calibração não medida por ECE |
| 1T Total | ✅ Sim | λ_ht calculado por média histórica HT separada | ❌ Desacoplado do modelo FT — inconsistência interna |
| 2T Total | ✅ Sim | `2T = FT - 1T` (diferença ingênua) | ❌ Derivação proibida — 2T não pode ser FT minus 1T via subtração |
| FT Casa | ✅ Sim | λ_home_ft via neural + splits históricos | ⚠️ Neural em shadow, mas contribui para output |
| FT Visitante | ✅ Sim | λ_away_ft via neural + splits históricos | ⚠️ Idem |
| 1T Casa | ⚠️ Parcial | Média histórica home_ht separada | ❌ Sem vínculo com modelo base |
| 1T Visitante | ⚠️ Parcial | Média histórica away_ht separada | ❌ Idem |
| 2T Casa | ⚠️ Parcial | `2T_home = FT_home - 1T_home` | ❌ Derivação ingênua |
| 2T Visitante | ⚠️ Parcial | `2T_away = FT_away - 1T_away` | ❌ Derivação ingênua |

---

## 2. Diagnóstico por Família de Mercado

### 2.1 FT Total — PARCIALMENTE VÁLIDO

**O que funciona:**
- LightGBM + RF Stacking com objetivo Tweedie é adequado para overdispersão
- Bivariate Poisson captura correlação entre home/away
- FeatureStore como única fonte de truth para features

**O que falha:**
- Output final é blend champion + challenger (`final_conf = champion*0.5 + prob_score*0.5`)
- ECE nunca é medido — calibração é assumida
- Monte Carlo não tem calibração ground-truth
- `clip(lower=3.0)` aplicado sem ablação

**Ação necessária:** Limpar o blend; manter apenas champion como output oficial; medir ECE.

---

### 2.2 1T Total — INVÁLIDO (desacoplado)

**Problema raiz:**
```python
# statistical.py:589-603
h_corners_ht = df_home['corners_home_ht']  # média histórica separada
# não há vínculo com λ_home_ft do modelo
```

O modelo FT prevê `λ_home_ft` + `λ_away_ft`. O modelo HT usa uma média histórica completamente separada. Isso viola a coerência:
$$\lambda_{FT} \neq \lambda_{1H} + \lambda_{2H}$$

quando `λ_1H` vem de uma fonte diferente de `λ_FT`.

**Ação necessária:** Modelar explicitamente `[home_1H, away_1H]` dentro da distribuição conjunta.

---

### 2.3 2T Total — INVÁLIDO (derivação ingênua proibida)

**Código violador:**
```python
# bet_resolver.py:23 e bet_validator.py:122
total_2h = total_ft - total_ht
```

Esta derivação usa FT e HT como se fossem independentes. O problema:
- `total_ft` vem do modelo champion (Tweedie)
- `total_ht` vem de média histórica HT
- A subtração mistura duas fontes diferentes criando variância artificial

**A abordagem correta:** Modelar `home_2H` e `away_2H` como componentes do vetor latente, com:
$$\text{home\_ft} = \text{home\_1H} + \text{home\_2H}$$
$$\text{away\_ft} = \text{away\_1H} + \text{away\_2H}$$

---

### 2.4 Mercados por Time (FT Home, FT Away) — PARCIALMENTE VÁLIDO COM RESSALVA

**O que funciona:**
- Neural challenger prediz `(λ_home, λ_away)` separados
- Bivariate Poisson simula correlação

**O que falha:**
- Neural challenger está em shadow mode mas seu λ contribui para o output final
- `SelectionStrategy` usa `fair_odd >= 1.25` como filtro sem justificativa empírica

---

### 2.5 Mercados 1T/2T por Time — INVÁLIDOS

**Status:** Calculados por splits de médias históricas HT independentes.
**Não há:** Vínculo com a distribuição joint do modelo. Consistência não verificada.

---

## 3. Problemas de Calibração Identificados

### 3.1 Calibrador Global vs. Por Família

O arquivo `calibrator_temperature.pkl` carregado pelo ManagerAI é um único calibrador de temperatura para FT total. Não existem calibradores para:

| Família | Calibrador Existente |
|---|---|
| FT total | ⚠️ Existe, mas global (temperatura única) |
| 1T total | ❌ Não existe |
| 2T total | ❌ Não existe |
| FT Casa | ❌ Não existe |
| FT Visitante | ❌ Não existe |
| 1T Casa | ❌ Não existe |
| 1T Visitante | ❌ Não existe |
| 2T Casa | ❌ Não existe |
| 2T Visitante | ❌ Não existe |

### 3.2 Ausência de Medição de Calibração

O sistema **nunca mede** ECE (Expected Calibration Error) em produção. A calibração é assumida porque um calibrador foi ajustado, sem verificação periódica.

**Sintoma observado no código:**
```python
# manager_ai.py:190-211
final_conf = (champion_conf * 0.5 + prob_score * 0.5) * agreement
# não há verificação de calibração neste cálculo
```

---

## 4. Problemas de Ranking e Seleção

### 4.1 Critérios Heurísticos Ativos (sem ablação)

| Critério | Onde | Problema |
|---|---|---|
| `rank_score = consensus_confidence` | `selection_strategy.py:44` | Confiança bruta não calibrada como ranking |
| Easy >= 60%, Medium 50-60%, Hard 40-50% | `statistical.py` | Limiares fixos sem evidência empírica |
| `FairOdd >= 1.25` | `statistical.py:generate_suggestions()` | Filtra por valor teórico sem odd real |
| Top 7 | `unified_scanner.py:313` | Número fixo sem justificativa por volume |

### 4.2 Critérios Proibidos em Uso

| Critério Proibido | Onde Aparece |
|---|---|
| Easy/Medium/Hard | `statistical.py`, interface web |
| FairOdd como ranking oficial | `selection_strategy.py`, `unified_scanner.py` |
| Top 7 como output oficial | `unified_scanner.py:313` |

---

## 5. Resumo para Ação Imediata

### P0 — Crítico (viola diretrizes fundamentais):
1. **Separar champion do challenger no output** — `manager_ai.py` 
2. **Remover derivação 2T = FT - 1T** — `bet_resolver.py`, `bet_validator.py`
3. **Criar vetor latente [home_1H, away_1H, home_2H, away_2H]** — novo módulo

### P1 — Alto (invalida mercados HT/2T):
4. **Criar calibradores por família** — 9 calibradores dedicados
5. **Medir ECE em pipeline de treino** — `training/trainer.py`

### P2 — Médio (ranking e governança):
6. **Substituir Easy/Medium/Hard por ranking calibrado** 
7. **Adicionar critérios de calibração por família em ModelRegistry**
8. **Ablação formal da winsorização clip(3.0)**
