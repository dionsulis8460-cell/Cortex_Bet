"""
Trainer Module - Cortex ML V2.1
Handles model training, hyperparameter optimization, and transfer learning.
"""

import os
import sys
import traceback
import pandas as pd
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features
from src.models.model_v2 import ProfessionalPredictor
from src.utils.reproducibility import set_global_seeds, save_run_metadata, get_dataset_hash

def _fix_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Helper para corrigir nomes de colunas."""
    if df.empty: return df
    df = df.copy()
    if 'home_score' in df.columns and 'goals_ft_home' not in df.columns:
        df['goals_ft_home'] = df['home_score']
    if 'away_score' in df.columns and 'goals_ft_away' not in df.columns:
        df['goals_ft_away'] = df['away_score']
    return df

def train_model(args=None) -> None:
    """
    Treina o modelo de Machine Learning utilizando o pipeline Professional V2.
    """
    # 🔒 AUDIT CHECK: Reproducibility
    SEED = 42
    set_global_seeds(SEED)
    
    print("\n" + "=" * 50)
    print("Escolha o modo de treinamento:")
    print("1. Treinamento Padrão (Rápido)")
    print("2. Otimizar Modelo - AutoML (Optuna)")
    print("3. Transfer Learning (Global + Por Liga)")
    print("4. Optuna + Transfer Learning [RECOMENDADO]")
    print("5. 🤖 Neural Challenger (MLP Multi-Output)")
    print("=" * 50)
    
    mode_choice = None
    # Priority: 1. Command-line args, 2. Environment variables, 3. Interactive input
    if args and hasattr(args, 'train') and args.train:
        mode_choice = str(args.train)
    elif os.getenv('CORTEX_TRAIN_MODE'):
        mode_choice = os.getenv('CORTEX_TRAIN_MODE')
        print(f"[ENV] Modo de treinamento: {mode_choice}")
    else:
        mode_choice = input("Opção (1-5): ").strip()

    use_optuna = mode_choice == '2'
    use_transfer = mode_choice == '3'
    use_full = mode_choice == '4'
    use_neural = mode_choice == '5'
    
    # IA 2: Neural Challenger (pipeline separado)
    if use_neural:
        print("\n🤖 Iniciando Treinamento do Neural Challenger (MLP Multi-Output)...")
        n_trials = 20
        if args and hasattr(args, 'trials') and args.trials:
            n_trials = args.trials
        elif os.getenv('CORTEX_N_TRIALS'):
            n_trials = int(os.getenv('CORTEX_N_TRIALS'))
        else:
            n_trials_input = input("Quantos trials do Optuna? (padrão: 20): ").strip()
            n_trials = int(n_trials_input) if n_trials_input.isdigit() else 20
        
        from src.ml.train_neural import train_neural_model
        import argparse
        neural_args = argparse.Namespace(experiment='Neural_CLI', optuna=True, trials=n_trials)
        train_neural_model(neural_args)
        return
    
    db = DBManager()
    df = db.get_historical_data()
    db.close()
    
    if df.empty:
        print("Banco de dados vazio. Execute a atualização primeiro.")
        return
        
    print(f"Carregados {len(df)} registros para treino.")
    df = _fix_column_names(df)
    
    print("\n🚀 Iniciando Treinamento Cortex V2.1 (Academic Stable)...")
    print("🔧 Gerando features avançadas (Home/Away, H2H, Momentum)...")
    
    try:
        # AUDIT FIX: unpacking 4 values
        X, y, timestamps, _ = create_advanced_features(df, window_short=3, window_long=5)
        
        print(f"📊 Features geradas: {X.shape[1]} colunas, {X.shape[0]} amostras")
        odds = None # No odds support in current feature set
        
        predictor = ProfessionalPredictor()
        
        if use_full:
            # MELHOR OPÇÃO: Optuna + Transfer Learning + Calibração
            n_trials = 50
            if args and hasattr(args, 'trials') and args.trials:
                n_trials = args.trials
            elif os.getenv('CORTEX_N_TRIALS'):
                n_trials = int(os.getenv('CORTEX_N_TRIALS'))
            else:
                n_trials_input = input("Quantos trials do Optuna? (padrão: 50): ").strip()
                n_trials = int(n_trials_input) if n_trials_input.isdigit() else 50
            
            print(f"\n🔥 FASE 1: Otimização com Optuna ({n_trials} trials)...")
            best_params = predictor.optimize_hyperparameters(X, y, timestamps, n_trials=n_trials)
            print(f"✅ Melhores parâmetros: {best_params}")
            
            print("\n🌍 FASE 2: Transfer Learning com parâmetros otimizados...")
            tournament_ids = X['tournament_id'] if 'tournament_id' in X.columns else None
            predictor.train_global_and_finetune(X, y, timestamps, tournament_ids, odds=odds)
            
            print("\n🌡️ FASE 3: Treinando Calibrador de Produção...")
            from src.scripts.save_production_calibrator import save_calibrator
            save_calibrator()
            
            print("\n✅ Full Pipeline (Optuna + Transfer + Calibration) concluído!")
            
        elif use_transfer:
            print("\n🌍 Iniciando Transfer Learning (Global + Por Liga)...")
            tournament_ids = X['tournament_id'] if 'tournament_id' in X.columns else None
            predictor.train_global_and_finetune(X, y, timestamps, tournament_ids, odds=odds)
            print("\n✅ Transfer Learning concluído!")
            
        elif use_optuna:
            n_trials = 50
            if args and hasattr(args, 'trials') and args.trials:
                n_trials = args.trials
            else:
                n_trials_input = input("Quantos trials do Optuna? (padrão: 50, recomendado: 50-100): ").strip()
                n_trials = int(n_trials_input) if n_trials_input.isdigit() else 50
            print(f"\n🔥 Iniciando Otimização com Optuna ({n_trials} trials)...")
            best_params = predictor.optimize_hyperparameters(X, y, timestamps, n_trials=n_trials)
            print(f"\n✅ Melhores parâmetros encontrados: {best_params}")
            print("\n📈 Treinando modelo final com parâmetros otimizados...")
            predictor.train_time_series_split(X, y, timestamps, odds=odds)
            print("\n✅ Modelo salvo com sucesso!")
            
        else:
            # Treinamento padrão (com Strict Holdout do Audit Plan)
            predictor.train_time_series_split(X, y, timestamps, odds=odds, holdout_frac=0.15)
            print("\n✅ Modelo salvo com sucesso!")
        
        # 📝 AUDIT CHECK: Save Metadata
        data_hash = get_dataset_hash(df)
        save_run_metadata("data/last_run_metadata.json", seed=SEED, extra_info={'dataset_hash': data_hash, 'rows': len(df)})
        
    except Exception as e:
        print(f"❌ Erro fatal no treinamento: {e}")
        traceback.print_exc()
