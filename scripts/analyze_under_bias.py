#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Análise de Viés UNDER nas Previsões
Investiga por que o sistema está gerando muitas previsões UNDER
"""

import sqlite3
import pandas as pd
import statistics
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to database
conn = sqlite3.connect('data/bet_system.db')

# Get all tables
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tabelas disponiveis: {[t[0] for t in tables]}\n")

# Query recent predictions
print("=" * 80)
print("ANÁLISE 1: Distribuição Over vs Under nas Previsões")
print("=" * 80)

query = """
SELECT 
    prediction_label,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(value) as avg_value
FROM match_predictions
WHERE category = 'Top7'
AND prediction_label IS NOT NULL
GROUP BY CASE 
    WHEN LOWER(prediction_label) LIKE '%over%' THEN 'Over'
    WHEN LOWER(prediction_label) LIKE '%under%' THEN 'Under'
    ELSE 'Other'
END
"""

try:
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))
except Exception as e:
    print(f"Erro query 1: {e}")

print("\n" + "=" * 80)
print("ANÁLISE 2: Distribuição de Linhas Escolhidas")
print("=" * 80)

query2 = """
SELECT 
    CASE 
        WHEN value < 8.5 THEN '< 8.5 (Muito Baixo)'
        WHEN value >= 8.5 AND value < 10.5 THEN '8.5-10.5 (Baixo)'
        WHEN value >= 10.5 AND value < 12.5 THEN '10.5-12.5 (Médio)'
        WHEN value >= 12.5 THEN '>= 12.5 (Alto)'
    END as linha_range,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM match_predictions
WHERE category = 'Top7'
AND value > 0
GROUP BY linha_range
ORDER BY MIN(value)
"""

try:
    df2 = pd.read_sql_query(query2, conn)
    print(df2.to_string(index=False))
except Exception as e:
    print(f"Erro query 2: {e}")

print("\n" + "=" * 80)
print("ANÁLISE 3: Previsões ML (Valor Bruto do Modelo)")
print("=" * 80)

query3 = """
SELECT 
    AVG(value) as media_lambda,
    MIN(value) as min_lambda,
    MAX(value) as max_lambda,
    COUNT(*) as total,
    SUM(CASE WHEN value < 9.5 THEN 1 ELSE 0 END) as abaixo_9_5,
    SUM(CASE WHEN value >= 9.5 THEN 1 ELSE 0 END) as acima_9_5
FROM match_predictions
WHERE category = 'Professional'
AND value > 0
"""

try:
    df3 = pd.read_sql_query(query3, conn)
    print(df3.to_string(index=False))
    total = df3['total'].iloc[0]
    abaixo = df3['abaixo_9_5'].iloc[0]
    acima = df3['acima_9_5'].iloc[0]
    print(f"\nDistribuicao ML:")
    print(f"   < 9.5: {abaixo} ({abaixo/total*100 if total else 0:.1f}%)")
    print(f"  >= 9.5: {acima} ({acima/total*100 if total else 0:.1f}%)")
except Exception as e:
    print(f"Erro query 3: {e}")

print("\n" + "=" * 80)
print("ANÁLISE 4: Últimas 50 Previsões Top 7")
print("=" * 80)

query4 = """
SELECT 
    prediction_label,
    value,
    confidence,
    created_at
FROM match_predictions
WHERE category = 'Top7'
ORDER BY id DESC
LIMIT 50
"""

try:
    df4 = pd.read_sql_query(query4, conn)
    overs = df4[df4['prediction_label'].str.lower().str.contains('over', na=False)]
    unders = df4[df4['prediction_label'].str.lower().str.contains('under', na=False)]
    
    print(f"Últimas 50 previsões Top 7:")
    print(f"   Over: {len(overs)} ({len(overs)/len(df4)*100:.1f}%)")
    print(f"   Under: {len(unders)} ({len(unders)/len(df4)*100:.1f}%)")
    print(f"\nExemplos de Under:")
    print(unders[['prediction_label', 'value', 'confidence']].head(10).to_string(index=False))
except Exception as e:
    print(f"Erro query 4: {e}")

conn.close()

print("\n" + "=" * 80)
print("CONCLUSÃO DA INVESTIGAÇÃO")
print("=" * 80)
print("""
Próximos passos:
1. Se > 60% são Under → Viés confirmado
2. Verificar se ML está prevendo lambda < 9.5 sistematicamente
3. Analisar lógica de seleção de Over/Under no código
4. Propor correção
"""
)
