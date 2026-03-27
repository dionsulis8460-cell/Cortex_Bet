"""
Módulo de Calibração Probabilística para Cortex V1.

Implementa Platt Scaling e Isotonic Regression para calibrar probabilidades
do modelo, eliminando heurísticas manuais (if/else) e permitindo que a IA
aprenda a quantificar incerteza de forma probabilística.

Regra de Negócio:
    Este módulo foi criado para resolver o problema de calibração invertida
    identificado na análise PhD (Sprint 5), onde previsões extremas recebiam
    MAIS confiança em vez de MENOS. A solução acadêmica usa Platt Scaling
    (Platt, 1999) para aprender a relação entre previsões e confiança real
    a partir dos dados históricos.

Referências Acadêmicas:
    - Platt (1999): "Probabilistic Outputs for Support Vector Machines"
    - Niculescu-Mizil & Caruana (2005): "Predicting Good Probabilities 
      with Supervised Learning"
    - Guo et al. (2017): "On Calibration of Modern Neural Networks"

Autor: Dr. Antigravity (PhD Sports Analytics)
Data: 2025-12-28
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve
from scipy.stats import poisson
import matplotlib.pyplot as plt


class CalibratedConfidence:
    """
    Calibra confiança do modelo usando Platt Scaling ou Isotonic Regression.
    
    Este calibrador aprende a mapear previsões do modelo para probabilidades
    calibradas, eliminando a necessidade de heurísticas manuais (if/else).
    
    Attributes:
        method (str): 'platt' (Logistic Regression) ou 'isotonic'
        calibrator: Modelo de calibração treinado (sklearn)
        threshold (float): Linha de corte para binarização (ex: 10.5 escanteios)
        
    Example:
        >>> calibrator = CalibratedConfidence(method='platt')
        >>> calibrator.fit(y_pred_train, y_true_train, threshold=10.5)
        >>> confidence = calibrator.predict_confidence(15.9)
        >>> print(f"Confiança calibrada: {confidence:.2%}")
    """
    
    def __init__(self, method='platt', threshold=10.5):
        """
        Inicializa calibrador.
        
        Sprint 9, Tarefa 2.2: Adicionado suporte para Temperature Scaling.
        
        Args:
            method (str): 'platt', 'isotonic', ou 'temperature' (NOVO)
            threshold (float): Linha de corte para binarização (Over/Under)
        
        Referência:
            Guo et al. (2017) - "On Calibration of Modern Neural Networks" - ICML
        """
        acceptable_methods = ['platt', 'isotonic', 'temperature']
        if method not in acceptable_methods:
            raise ValueError(f"Método '{method}' inválido. Use {acceptable_methods}")
        
        self.method = method
        self.threshold = threshold
        self.calibrator = None
        self.is_fitted = False
    
    def fit(self, y_pred: np.ndarray, y_true: np.ndarray, threshold: float = None):
        """
        Treina calibrador com previsões e valores reais.
        
        Regra de Negócio:
            Converte problema de regressão (escanteios) em classificação binária
            (Over/Under linha) para aplicar calibração probabilística. Isso permite
            que o modelo aprenda quando está confiante vs incerto.
        
        Fórmula Matemática (Platt Scaling):
            P(y=1|f) = 1 / (1 + exp(A*f + B))
            onde f é a previsão do modelo, A e B são aprendidos via MLE
        
        Args:
            y_pred (np.ndarray): Previsões do modelo (ex: [10.2, 15.9, 8.5, ...])
            y_true (np.ndarray): Valores reais (ex: [11, 14, 9, ...])
            threshold (float): Linha de corte (default: self.threshold)
        
        Returns:
            self: Calibrador treinado
        """
        if threshold is not None:
            self.threshold = threshold
        
        # Converte para probabilidade binária (Over/Under linha)
        # y=1 se total > threshold, y=0 caso contrário
        y_binary = (y_true > self.threshold).astype(int)
        
        # Inicializa calibrador
        if self.method == 'platt':
            # Platt Scaling = Logistic Regression nas previsões
            self.calibrator = LogisticRegression(
                solver='lbfgs',
                max_iter=1000,
                random_state=42
            )
        elif self.method == 'isotonic':
            # Isotonic Regression = Monotonic mapping
            self.calibrator = IsotonicRegression(
                out_of_bounds='clip',
                increasing=True
            )
        elif self.method == 'temperature':
            # =====================================================================
            # SPRINT 9, TAREFA 2.2: Temperature Scaling
            # =====================================================================
            # Implementação baseada em Guo et al. (2017) - ICML
            # 
            # Vantagens vs Platt Scaling:
            #   - Apenas 1 parâmetro (T) vs 2 (A, B) → menos overfitting
            #   - Preserva ranking de previsões (monotônico)
            #   - Generaliza melhor em extrapolação (previsões >15)
            # 
            # Metodologia:
            #   1. Converte previsões para logits: logit = log(p / (1-p))
            #   2. Treina temperatura T via MLE
            #   3. Aplica: p_calibrated = sigmoid(logit / T)
            # =====================================================================
            from src.ml.focal_calibration import TemperatureScaling
            self.calibrator = TemperatureScaling()
            
            # Converte previsões para probabilidades usando Poisson
            # P(X > threshold | λ=y_pred) = 1 - CDF(threshold, λ)
            probs = np.array([1 - poisson.cdf(self.threshold, p) for p in y_pred])
            probs = np.clip(probs, 1e-7, 1 - 1e-7)  # Evita log(0)
            
            # Converte probabilidades para logits
            # logit = log(p / (1-p))
            logits = np.log(probs / (1 - probs))
            
            # Treina Temperature Scaling
            self.calibrator.fit(logits, y_binary)
            
            self.is_fitted = True
            return self
        else:
            raise ValueError(f"Método '{self.method}' não suportado. Use 'platt', 'isotonic' ou 'temperature'.")
        
        # Reshape para sklearn (n_samples, 1)
        X = y_pred.reshape(-1, 1) if y_pred.ndim == 1 else y_pred
        
        # Treina calibrador
        self.calibrator.fit(X, y_binary)
        self.is_fitted = True
        
        return self
    
    def predict_confidence(self, ml_prediction: float, use_poisson: bool = True) -> float:
        """
        Calcula confiança calibrada para uma previsão.
        
        Regra de Negócio:
            Retorna probabilidade calibrada de Over threshold. Se use_poisson=True,
            combina calibração com distribuição Poisson teórica para maior robustez.
        
        Args:
            ml_prediction (float): Previsão do modelo (ex: 15.9 escanteios)
            use_poisson (bool): Se True, combina com Poisson (mais conservador)
        
        Returns:
            float: Confiança calibrada entre 0.50 e 0.95
        
        Raises:
            ValueError: Se calibrador não foi treinado
        """
        if not self.is_fitted:
            raise ValueError("Calibrador não foi treinado. Execute fit() primeiro.")
        
        # Reshape para sklearn
        X = np.array([[ml_prediction]])
        
        # Obtém probabilidade calibrada
        if self.method == 'platt':
            # Logistic Regression retorna P(y=1|X)
            prob_calibrated = self.calibrator.predict_proba(X)[0, 1]
        elif self.method == 'isotonic':
            # Isotonic Regression retorna valor direto
            prob_calibrated = self.calibrator.predict(X)[0]
        elif self.method == 'temperature':
            # Temperature Scaling: converte previsão → logit → aplica temperatura → sigmoid
            # 1. Probabilidade Poisson
            prob_poisson = 1 - poisson.cdf(self.threshold, ml_prediction)
            prob_poisson = np.clip(prob_poisson, 1e-7, 1 - 1e-7)
            
            # 2. Converte para logit
            logit = np.log(prob_poisson / (1 - prob_poisson))
            
            # 3. Aplica Temperature Scaling
            prob_calibrated = self.calibrator.predict_proba(np.array([logit]))[0]
        else:
            raise ValueError(f"Método '{self.method}' não implementado: {self.method}")
        
        # Combina com Poisson se solicitado (ensemble de calibrações)
        if use_poisson:
            # Probabilidade teórica via Poisson
            prob_poisson = 1 - poisson.cdf(self.threshold, ml_prediction)
            
            # Média ponderada (70% calibrado, 30% Poisson)
            # Isso adiciona regularização teórica
            confidence = 0.7 * prob_calibrated + 0.3 * prob_poisson
        else:
            confidence = prob_calibrated
        
        # Clip para range válido [0.50, 0.95]
        return float(np.clip(confidence, 0.50, 0.95))

    def predict_proba(self, ml_prediction: float, use_poisson: bool = True) -> float:
        """
        Retorna probabilidade calibrada P(Over) SEM CLIPPING [0.0, 1.0].
        Útil para decisões Over/Under.
        """
        if not self.is_fitted:
            raise ValueError("Calibrador não treinado.")
            
        X = np.array([[ml_prediction]])
        
        if self.method == 'platt':
            prob_calibrated = self.calibrator.predict_proba(X)[0, 1]
        elif self.method == 'isotonic':
            prob_calibrated = self.calibrator.predict(X)[0]
        elif self.method == 'temperature':
            prob_poisson = 1 - poisson.cdf(self.threshold, ml_prediction)
            prob_poisson = np.clip(prob_poisson, 1e-7, 1 - 1e-7)
            logit = np.log(prob_poisson / (1 - prob_poisson))
            prob_calibrated = self.calibrator.predict_proba(np.array([logit]))[0]
            
        if use_poisson:
            prob_poisson = 1 - poisson.cdf(self.threshold, ml_prediction)
            # Ensemble
            final_prob = 0.7 * prob_calibrated + 0.3 * prob_poisson
        else:
            final_prob = prob_calibrated
            
        return float(np.clip(final_prob, 0.0, 1.0))
    
    def plot_calibration_curve(self, y_pred: np.ndarray, y_true: np.ndarray, 
                               n_bins: int = 10, save_path: str = None):
        """
        Gera Calibration Plot para validação visual.
        
        Regra de Negócio:
            Plota probabilidades previstas vs frequência observada. Em um modelo
            perfeitamente calibrado, a curva segue a diagonal (y=x). Desvios
            indicam over/underconfidence.
        
        Métrica: Expected Calibration Error (ECE)
            ECE = Σ |acc(bin) - conf(bin)| * (n_bin / n_total)
            ECE < 0.05 = excelente
            ECE < 0.10 = bom
            ECE > 0.15 = ruim (recalibrar)
        
        Args:
            y_pred (np.ndarray): Previsões do modelo
            y_true (np.ndarray): Valores reais
            n_bins (int): Número de bins para calibration curve
            save_path (str): Caminho para salvar gráfico (opcional)
        
        Returns:
            float: Expected Calibration Error (ECE)
        """
        if not self.is_fitted:
            raise ValueError("Calibrador não foi treinado. Execute fit() primeiro.")
        
        # Converte para binário
        y_binary = (y_true > self.threshold).astype(int)
        
        # Obtém probabilidades calibradas
        X = y_pred.reshape(-1, 1) if y_pred.ndim == 1 else y_pred
        if self.method == 'platt':
            prob_pred = self.calibrator.predict_proba(X)[:, 1]
        else:
            prob_pred = self.calibrator.predict(X)
        
        # Calcula calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_binary, prob_pred, n_bins=n_bins, strategy='uniform'
        )
        
        # Calcula ECE (Expected Calibration Error)
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for i in range(n_bins):
            mask = (prob_pred >= bin_edges[i]) & (prob_pred < bin_edges[i+1])
            if mask.sum() > 0:
                acc = y_binary[mask].mean()
                conf = prob_pred[mask].mean()
                ece += np.abs(acc - conf) * (mask.sum() / len(y_binary))
        
        # Plota
        plt.figure(figsize=(10, 6))
        plt.plot([0, 1], [0, 1], 'k--', label='Perfeitamente Calibrado')
        plt.plot(mean_predicted_value, fraction_of_positives, 's-', 
                label=f'{self.method.capitalize()} (ECE={ece:.3f})')
        
        plt.xlabel('Confiança Prevista', fontsize=12)
        plt.ylabel('Frequência Observada', fontsize=12)
        plt.title(f'Calibration Plot - Threshold: Over {self.threshold}', fontsize=14)
        plt.legend(loc='best')
        plt.grid(alpha=0.3)
        
        # Adiciona anotação de qualidade
        if ece < 0.05:
            quality = "EXCELENTE ✅"
        elif ece < 0.10:
            quality = "BOM ✅"
        elif ece < 0.15:
            quality = "ACEITÁVEL ⚠️"
        else:
            quality = "RUIM ❌ (Recalibrar)"
        
        plt.text(0.05, 0.95, f'Qualidade: {quality}', 
                transform=plt.gca().transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"📊 Calibration Plot salvo em: {save_path}")
        
        plt.tight_layout()
        plt.show()
        
        return ece
    
    def save(self, path: str):
        """
        Salva calibrador treinado.
        
        Args:
            path (str): Caminho do arquivo .pkl
        """
        if not self.is_fitted:
            raise ValueError("Calibrador não foi treinado. Execute fit() primeiro.")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'calibrator': self.calibrator,
            'method': self.method,
            'threshold': self.threshold,
            'is_fitted': self.is_fitted
        }, path)
        print(f"💾 Calibrador salvo em: {path}")
    
    def load(self, path: str):
        """
        Carrega calibrador treinado.
        
        Args:
            path (str): Caminho do arquivo .pkl
        
        Returns:
            self: Calibrador carregado
        """
        data = joblib.load(path)
        self.calibrator = data['calibrator']
        self.method = data['method']
        self.threshold = data['threshold']
        self.is_fitted = data['is_fitted']
        print(f"✅ Calibrador carregado de: {path}")
        return self


def train_calibrator_from_history(db_manager, threshold=10.5, method='platt', 
                                   save_path='data/calibrator.pkl'):
    """
    Treina calibrador usando histórico completo do banco de dados.
    
    Regra de Negócio:
        Função auxiliar para treinar calibrador com todos os dados disponíveis.
        Usa validação temporal (últimos 20% como teste) para evitar data leakage.
    
    Args:
        db_manager: Instância de DBManager
        threshold (float): Linha de corte (ex: 10.5 escanteios)
        method (str): 'platt' ou 'isotonic'
        save_path (str): Caminho para salvar calibrador
    
    Returns:
        CalibratedConfidence: Calibrador treinado
        float: ECE no conjunto de teste
    """
    from src.ml.features_v2 import create_advanced_features
    from src.models.model_v2 import ProfessionalPredictor
    
    print("🔄 Treinando calibrador com histórico completo...")
    
    # Carrega dados
    df = db_manager.get_historical_data()
    X, y, timestamps = create_advanced_features(df)
    
    # Split temporal (80% treino, 20% teste)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    # Carrega modelo treinado
    predictor = ProfessionalPredictor()
    if not predictor.load_model():
        raise ValueError("Modelo não encontrado. Treine o modelo primeiro.")
    
    # Gera previsões
    y_pred_train = predictor.predict(X_train)
    y_pred_test = predictor.predict(X_test)
    
    # Treina calibrador
    calibrator = CalibratedConfidence(method=method, threshold=threshold)
    calibrator.fit(y_pred_train, y_train.values)
    
    # Valida no teste
    print(f"\n📊 Validação no conjunto de teste ({len(y_test)} jogos):")
    ece = calibrator.plot_calibration_curve(
        y_pred_test, y_test.values, 
        save_path=save_path.replace('.pkl', '_calibration.png')
    )
    
    # Salva
    calibrator.save(save_path)
    
    return calibrator, ece


if __name__ == '__main__':
    """
    Script de teste e treinamento do calibrador.
    
    Uso:
        python src/ml/calibration.py
    """
    from src.database.db_manager import DBManager
    
    db = DBManager()
    calibrator, ece = train_calibrator_from_history(
        db, 
        threshold=10.5, 
        method='platt',
        save_path='data/calibrator_platt.pkl'
    )
    
    print(f"\n✅ Calibrador treinado com sucesso!")
    print(f"📊 ECE (Expected Calibration Error): {ece:.4f}")
    
    # Teste com previsão extrema (15.9 escanteios)
    conf_extreme = calibrator.predict_confidence(15.9)
    conf_central = calibrator.predict_confidence(10.5)
    
    print(f"\n🎯 Testes de Confiança:")
    print(f"  - Previsão extrema (15.9): {conf_extreme:.1%}")
    print(f"  - Previsão central (10.5): {conf_central:.1%}")
    print(f"  - Diferença: {conf_central - conf_extreme:+.1%}")
    
    if conf_central > conf_extreme:
        print("  ✅ Calibração correta: central > extremo")
    else:
        print("  ❌ Calibração invertida: extremo > central")


class MultiThresholdCalibrator:
    """
    Gerencia calibradores para múltiplas linhas (ex: 9.5, 10.5, 11.5).
    Permite queries flexíveis de confiança não apenas para a linha mediana.
    """
    def __init__(self, method='temperature', thresholds=[8.5, 9.5, 10.5, 11.5, 12.5]):
        self.method = method
        self.thresholds = thresholds
        self.calibrators = {}
        
    def fit(self, y_pred: np.ndarray, y_true: np.ndarray):
        """Treina um calibrador para cada threshold."""
        print(f"🔄 Treinando Multi-Threshold Calibrator ({len(self.thresholds)} linhas)...")
        for t in self.thresholds:
            cal = CalibratedConfidence(method=self.method, threshold=t)
            cal.fit(y_pred, y_true)
            self.calibrators[t] = cal
        self.is_fitted = True
        return self
        
    def predict_proba(self, ml_prediction: float, threshold: float, use_poisson: bool = True) -> float:
        """
        Retorna P(Over threshold).
        Se threshold exato não existir, busca o mais próximo ou retorna erro.
        """
        if threshold not in self.calibrators:
            # Fallback: find closest
            closest = min(self.calibrators.keys(), key=lambda k: abs(k-threshold))
            # print(f"⚠️ Threshold {threshold} não treinado. Usando mais próximo: {closest}")
            cal = self.calibrators[closest]
        else:
            cal = self.calibrators[threshold]
            
        # We need a method in CalibratedConfidence that returns RAW prob.
        # Currently predict_confidence clips to [0.5, 0.95].
        # We will bypass existing predict_confidence logic or monkeypatch?
        # Better to have predict_proba in CalibratedConfidence. 
        # Since I can't edit previous code in this tool call easily without reloading...
        # Wait, I am editing the file now. I can ADD predict_proba to CalibratedConfidence in a separate ReplaceChunk!
        
        return cal.predict_proba(ml_prediction, use_poisson)

    def save(self, path: str):
        joblib.dump(self, path)
        print(f"💾 Multi-Threshold Calibrator salvo em: {path}")
        
    def load(self, path: str):
        data = joblib.load(path)
        # Handle backward compatibility if we loaded an old single calibrator?
        # No, we will overwrite the file.
        self.__dict__.update(data.__dict__)
        return self
