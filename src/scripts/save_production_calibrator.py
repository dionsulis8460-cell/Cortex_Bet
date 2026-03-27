"""
Script de Produção: Treinar e Salvar Calibrador (Temperature Scaling)

Este script deve ser executado para gerar o artefato 'calibrator_temperature.pkl'
que será usado pelo motor de previsões em produção.

Metodologia:
    1. Carrega dados históricos.
    2. Divide em Treino (Modelo) e Calibração (Calibrador).
    3. Treina Temperature Scaling para múltiplas linhas (9.5, 10.5, 11.5, 12.5).
    4. Salva o calibrador treinado em 'data/calibrator_temperature.pkl'.
"""

import sys
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import poisson

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features
from src.models.model_v2 import ProfessionalPredictor
from src.ml.calibration import CalibratedConfidence
from src.ml.focal_calibration import TemperatureScaling

def save_calibrator():
    print("\n" + "="*80)
    print("🚀 TREINAMENTO DE CALIBRADOR DE PRODUÇÃO (TEMPERATURE SCALING)")
    print("="*80)
    
    # 1. Carregar Dados
    print("📂 Carregando dados históricos...")
    db = DBManager()
    df = db.get_historical_data()
    X, y, timestamps, _ = create_advanced_features(df)
    
    # 2. Split (Manter consistência com validação: 80% Modelo / 20% Calibração)
    # Em produção, poderíamos usar Cross-Validation, mas para calibração pós-hoc
    # precisamos de previsões 'limpas' (não vistas pelo modelo).
    n = len(X)
    idx_split = int(n * 0.80)
    
    X_train = X.iloc[:idx_split]
    y_train = y.iloc[:idx_split]
    ts_train = timestamps.iloc[:idx_split]
    
    X_calib = X.iloc[idx_split:]
    y_calib = y.iloc[idx_split:]
    
    print(f"   Modelo Train: {len(X_train)} samples | Calibração: {len(X_calib)} samples")
    
    # 3. Treinar Modelo Base (ou carregar se já existir)
    # Para garantir alinhamento, vamos retreinar rápido ou carregar. 
    # Idealmente, carregamos o modelo de produção atual.
    model = ProfessionalPredictor()
    model_path = Path("data/corner_model_v2_professional.pkl")
    
    if model_path.exists():
        print("   Carregando modelo V2 existente...")
        model.load_model()
    else:
        print("   ⚠️ Modelo não encontrado. Treinando novo modelo base...")
        model.train_time_series_split(X_train, y_train, ts_train, n_splits=3)
        
    # Gera previsões no set de calibração
    print("   Gerando previsões para calibração...")
    preds_calib = model.predict(X_calib)
    
    # 4. Treinar Calibrador Temperature Scaling
    # O CalibratedConfidence pode gerenciar múltiplos thresholds ou um genérico.
    # No prediction_engine, usamos thresholds específicos ou o genérico?
    # O prediction_engine atual instancia `CalibratedConfidence()` sem args.
    # Vamos treinar um calibrador 'default' focado na linha mediana (10.5) 
    # mas que suporta o método temperature.
    
    # Melhora: Vamos criar um dicionário de calibradores por linha? 
    # O calibration.py atual suporta um threshold por vez no __init__.
    # Vamos treinar para a linha "padrão" de Over/Under (que o usuário vê como confiança principal).
    # O prediction_engine avalia a confiança da "best_bet" (ex: Over 11.5).
    # Precisamos de um sistema que suporte linha dinâmica.
    
    # Solução Pragmática Atual: Treinar para múltiplas linhas e salvar um objeto
    # que contém todos, ou salvar o arquivo padrão para a linha 10.5 (mediana).
    # Como o prediction_engine usa `predict_confidence(val, use_poisson=True)`,
    # ele converte a regra para probabilidade teórica. O Temperature Scaling
    # ajusta essa probabilidade.
    
    print("🌡️ Treinando Multi-Threshold Calibration (Temperature Scaling)...")
    
    # Instancia MultiThresholdCalibrator
    from src.ml.calibration import MultiThresholdCalibrator
    
    thresholds = [8.5, 9.5, 10.5, 11.5, 12.5, 13.5]
    calibrator = MultiThresholdCalibrator(method='temperature', thresholds=thresholds)
    
    # Treina para todas as linhas
    calibrator.fit(preds_calib, y_calib.values)
    
    # 5. Salvar Artefato
    output_path = "data/calibrator_temperature.pkl"
    calibrator.save(output_path)
        
    print(f"💾 Multi-Threshold Calibrator salvo em: {output_path}")
    print("\n✅ prediction_engine.py needs update to use this new class.")

if __name__ == "__main__":
    save_calibrator()
