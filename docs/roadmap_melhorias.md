# Roadmap de Melhorias - Cortex V3.0

**Última Atualização:** 05/02/2026

Este documento detalha as próximas melhorias planejadas para maximizar a performance do sistema de previsão.

---

## 🎯 Melhorias Priorizadas

### 1. **Ensemble de Múltiplos Modelos** 🔥 ALTA PRIORIDADE

**Objetivo:** Aumentar acurácia de 65% para 68-69%

**Implementação:**
- Adicionar XGBoost e CatBoost ao pipeline atual (que já usa LightGBM)
- Criar votação ponderada entre os 3 modelos
- Manter Temperature Scaling como calibrador final

**Impacto Esperado:**
- **Acurácia:** +3-4%
- **Robustez:** Redução de erros em jogos atípicos
- **Esforço:** Médio (1-2 semanas)

**Custo Computacional:** +200% tempo de treinamento (aceitável)

**Referência Acadêmica:** Dietterich (2000) - "Ensemble Methods in Machine Learning"

---

### 2. **Aumentar Trials do Optuna** 🔥 ALTA PRIORIDADE

**Objetivo:** Refinar hiperparâmetros para máxima performance

**Implementação:**
- Atual: 30 trials
- Meta: 100 trials (produção profissional)

**Impacto Esperado:**
- **Acurácia:** +1-2%
- **Esforço:** Baixo (apenas aumentar variável)
- **Tempo:** +2-3 horas de treinamento

---

### 3. **Features Contextuais** 🔥 ALTA PRIORIDADE

**Objetivo:** Capturar variáveis exógenas importantes

**Novas Features:**
- Clima (chuva reduz escanteios em ~15%)
- Árbitro (alguns marcam +30% mais escanteios)
- Importância do jogo (finais, clássicos)
- Lesões de jogadores-chave

**Impacto Esperado:**
- **Acurácia:** +2-3%
- **Esforço:** Médio (scraping de APIs externas)

**Referência:** Anderson & Sally (2013) - "The Numbers Game"

---

### 4. **Gaussian Processes para Incerteza** 🔥 ALTA PRIORIDADE ⚠️ CRÍTICO

> **⚠️ NOTA IMPORTANTE:** Sistema atualmente em produção com apostas reais. GP se torna essencial para gestão de risco e proteção de capital.

**Objetivo:** Melhorar gestão de risco para apostas reais

**Implementação:**
- Usar Sparse GP ou Variational GP (scalable)
- Fornecer intervalos de confiança (±1.2 escanteios)

**Impacto Esperado:**
- **Acurácia:** 0% (não altera predições)
- **Calibração:** +15-20% melhor estimativa de incerteza
- **ROI em Apostas:** +10-30% por gestão de risco
- **Drawdown:** -40% (proteção contra sequências negativas)
- **Esforço:** Alto (matemática bayesiana complexa)

**CRÍTICO para produção:** Implementar ANTES de aumentar stake

**Referência:** Rasmussen & Williams (2006) - "Gaussian Processes for ML"

---

## 📊 Comparação de Impacto

| Melhoria | Ganho Acurácia | Esforço | Custo Computacional | Prioridade |
|:---------|:---------------|:--------|:--------------------|:-----------|
| Ensemble | +3-4% | Médio | Alto | 🔥 Alta |
| Optuna 100 trials | +1-2% | Baixo | Alto | 🔥 Alta |
| Features Contextuais | +2-3% | Médio | Baixo | 🔥 Alta |
| Gaussian Processes | 0% (R OI +10-30%) | Alto | Muito Alto | 🔥 Alta ⚠️ |

---

## 🗓️ Cronograma Sugerido

### Semana 1-2: Quick Wins
- [x] Treinar com Optuna (30 trials) ✅ FEITO
- [ ] Aumentar para 100 trials
- [ ] Adicionar features de clima via Webscraping (ex: Sofascore)

### Semana 3-4: Ensemble
- [x] Implementar XGBoost ✅
- [x] Implementar CatBoost ✅
- [x] Sistema de votação ponderada ✅
- [x] Validação cruzada do ensemble ✅

### Semana 5-6: Refatoração e Arquitetura (Pós-Audit)
- [x] **Unificação:** Criar classe `ManagerAI` centralizada ✅
- [x] **Performance:** Feature Store para evitar cálculo duplicado (features_v2) ✅
- [x] **API:** Mover inferência para Async/Background Workers (Arquitetura Validada) ✅
- [x] **Testes:** Criar suite de testes para `prediction_engine.py` (Substituído por `test_manager_ai.py`) ✅
- [x] **Hotfix:** Corrigir erro de treino XGBoost (enable_categorical) ✅

### Semana 5-6: Refinamento
- [ ] Features de árbitros
- [ ] Features de importância do jogo
- [ ] Re-treinamento completo
- [ ] Backtest em temporada completa (12k jogos)

### Futuro (Opcional):
- [ ] Gaussian Processes (se apostas profissionais)
- [ ] Deep Learning (LSTM para séries temporais)

---

## � Frontend UX/UI - Monitoramento & Ensemble

### **Visão Geral**

Sistema de visualização moderno e profissional para expor métricas de performance e ensemble no `web_app` (Next.js).

**Páginas Novas:**
- `/performance` - Dashboard de métricas diárias
- `/analytics/compare` - Comparação de modelos Ensemble

---

### 1. **Dashboard de Performance Diária** 📊

**Componente:** `PerformanceOverview.tsx`

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  📈 Performance    🔄 Auto-refresh (30s)         │
├──────────────────────────────────────────────────┤
│  🎯 Analyst:  65.2% ↑  🏆 Manager: 100%  ↑     │
│  📊 RPS: 0.0752  ↓  🔥 Streak: 7 dias           │
│                                                   │
│  Acurácia (30 dias):                             │
│  ╭──────────────────────────────────────╮        │
│  │ 100%│          ●━━━━━●  Manager      │        │
│  │  80%│    ●━━●━━●  Analyst            │        │
│  │  60%│                                 │        │
│  │  40%┼┄┄┄┄┄┄┄┄┄ Baseline (50%)       │        │
│  ╰──────────────────────────────────────╯        │
└──────────────────────────────────────────────────┘
```

**Features:**
- ✅ Gráfico de linha (Recharts)
- ✅ Métricas principais em cards
- ✅ Streak atual e recorde
- ✅ Comparação com baseline (50%)

**Sistema de Alertas (Toast):**
```typescript
toast.warning('⚠️ Analyst AI: 52% (últimas 24h)')
toast.error('🔴 Manager AI: 3 erros consecutivos')
toast.success('✅ Modelo atualizado: RPS 0.0745')
```

---

### 2. **Ensemble Model Viewer** 🤖

**Componente:** `Ensemble Breakdown.tsx`

Exibido em **cada predição** do MatchCard:

```
┌─────────────────────────────────────────────┐
│  🎯 Final: 9.5 corners                      │
│  📊 Ensemble Confidence: 68% (High)         │
├─────────────────────────────────────────────┤
│  ⚡ LightGBM  9.3 ┃━━━━━━━━━┫ 65% (35%)    │
│  🚀 XGBoost  9.7 ┃━━━━━━━━━┫ 71% (35%)    │
│  🐈 CatBoost  9.5 ┃━━━━━━━━━┫ 68% (30%)    │
│                                              │
│  Consensus: ■━━━━━━━━━ High (Std: ±0.2)    │
│  💡 Todos modelos concordam! Alta conf.     │
└─────────────────────────────────────────────┘
```

**Tooltip ao passar mouse:**
```
⚡ LightGBM Details
─────────────────
Prediction: 9.3 corners
Confidence: 65%
Weight: 35%

Melhor em:
  • Features categóricas
  • Momentum temporal

✅ Treinado: 05/02/2026
   (Optuna 100 trials)
```

---

### 3. **Health Monitor Widget** 🏥

**Localização:** Header fixo (sempre visível)

```
┌────────────────────────────────────────┐
│  🟢 System Health: Excellent           │
│  Last 7d: ████████░░ 87%               │
│  Model: ✅ Updated 2h ago              │
│  Next retrain: 🕐 23h 14m              │
└────────────────────────────────────────┘
```

**Estados:**
- 🟢 **Excellent** (>70%): Verde
- 🟡 **Good** (60-70%): Amarelo
- 🟠 **Warning** (55-60%): Laranja pulsante
- 🔴 **Critical** (<55%): Vermelho pulsante

---

### 4. **Comparative Analysis** 📈

**Rota:** `/analytics/compare`

**Features:**
1. **Side-by-Side Models**
   - Acurácia por liga
   - Performance por linha (Over/Under)
   - ROI individual

2. **Feature Importance**
   ```
   LightGBM: Momentum (82%), H2H (71%)
   XGBoost:  Form (85%), Position (68%)
   CatBoost: Temporal (79%), Árbitro (65%)
   ```

3. **Heatmap de Concordância**
   ```
   Liga          | Alta (%) | Baixa (%)
   ──────────────────────────────────
   Premier League|    92    |    8
   Brasileirão   |    85    |   15
   La Liga       |    78    |   22
   ```

---

### 5. **Backend Monitoring API** 🔌

**Endpoints:**

```python
# src/api/monitoring.py

@app.get("/api/monitoring/health")
async def get_health():
    """System health + real-time metrics"""
    return {
        "status": "healthy",
        "analyst_7d": 0.652,
        "manager_7d": 1.00,
        "rps_trend": "improving",
        "alerts": []
    }

@app.get("/api/monitoring/daily-report")
async def get_daily_report(date: str):
    """Métricas detalhadas de um dia específico"""
    # Calcula acurácia
    # Compara com baseline
    # Gera alertas se <55%
    pass

@app.get("/api/ensemble/breakdown/{match_id}")
async def get_ensemble_details(match_id: int):
    """Detalhes de cada modelo no ensemble"""
    return {
        "lightgbm": {"pred": 9.3, "conf": 0.65},
        "xgboost": {"pred": 9.7, "conf": 0.71},
        "catboost": {"pred": 9.5, "conf": 0.68},
        "consensus": "high",
        "std_dev": 0.2
    }
```

**Auto-refresh Hook:**

```typescript
// web_app/hooks/useMonitoring.ts
function useMonitoring(interval = 30000) {
  const [metrics, setMetrics] = useState(null);
  
  useEffect(() => {
    const fetch = async () => {
      const res = await fetch('/api/monitoring/health');
      const data = await res.json();
      setMetrics(data);
      
      // Trigger alerts
      if (data.analyst_7d < 0.55) {
        toast.error('⚠️ Performance crítica!');
      }
    };
    
    fetch();
    const timer = setInterval(fetch, interval);
    return () => clearInterval(timer);
  }, []);
  
  return metrics;
}
```

---

## 📋 Cronograma de Implementação Frontend

### **Fase 1: Backend (3-4 dias)**
- [ ] `monitor_performance.py` (métricas diárias)
- [ ] Endpoints `/api/monitoring/*`
- [ ] Cron job (roda 23h todo dia)

### **Fase 2: Frontend Core (4-5 dias)**
- [ ] `PerformanceOverview.tsx`
- [ ] Gráficos Recharts
- [ ] Toast notifications
- [ ] Health Monitor widget

### **Fase 3: Ensemble UI (3-4 dias)**
- [ ] `EnsembleBreakdown.tsx`
- [ ] Consensus gauge
- [ ] Model tooltips
- [ ] Heatmap comparativo

### **Fase 4: Polish (2-3 dias)**
- [ ] Animações Framer Motion
- [ ] Responsividade mobile
- [ ] Dark mode
- [ ] Memoization (performance)

**Total:** 12-16 dias (~2-3 semanas)

---

## 💰 Valor Agregado (Produção)

| Feature | Benefício | ROI Estimado |
|:--------|:----------|:-------------|
| Monitoramento 24h | Detecta falhas <24h | Previne R$500-1000/semana |
| Alertas Auto | Ação imediata | Evita sequências negativas |
| Ensemble Transparency | +10-15% confiança | Aumenta stake em consenso alto |
| Comparative Analytics | Otimiza seleção | Melhora picks |

**ROI Total:** +15-25% pela gestão de risco

---

## 💡 Notas Importantes

**Estado Atual:**
- ✅ Analyst AI: 65% acurácia
- ✅ Manager AI: 100% acurácia (7/7)
- ✅ Sistema APROVADO para produção

**Metas:**
- Curto Prazo: 70% (estado da arte)
- Longo Prazo: 75% (limite teórico)

**Limitações Científicas:**
- Futebol tem ~40% aleatoriedade intrínseca
- Acurácia >80% é impossível sem info privilegiada
- Foco: ROI, não apenas acurácia
