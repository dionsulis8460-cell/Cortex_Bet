"""
Reproducibility Utilities for Cortex ML System.
Ensures deterministic runs and tracks experiment metadata.
"""

import os
import sys
import random
import numpy as np
import hashlib
import subprocess
import json
from datetime import datetime

def set_global_seeds(seed: int = 42) -> None:
    """
    Sets global seeds for Python, NumPy, and other observed libraries.
    Essential for audit reproducibility.
    """
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    
    # Se existirem outras libs sensíveis (PyTorch, TensorFlow), setar aqui.
    try:
        import lightgbm as lgb
        # LightGBM seeds are usually passed in params, but good to know
    except ImportError:
        pass
        
    print(f"[Reproducibility] Global Seed Locked: {seed}")

def get_git_info() -> dict:
    """Returns basic git metadata (sha, branch)."""
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
        return {'git_sha': sha, 'git_branch': branch}
    except Exception:
        return {'git_sha': 'unknown', 'git_branch': 'unknown'}

def get_dataset_hash(df) -> str:
    """Calculates a quick hash of the dataframe (integrity check)."""
    try:
        # Pega uma amostra determinística ou hash do objeto pandas
        return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()
    except Exception:
        return "hashing_failed"

def save_run_metadata(output_path: str, seed: int, extra_info: dict = None):
    """Saves run metadata to a JSON file."""
    import pandas as pd # lazy import
    
    meta = {
        'timestamp': datetime.now().isoformat(),
        'seed': seed,
        'python_version': sys.version,
        **get_git_info(),
        **(extra_info or {})
    }
    
    with open(output_path, 'w') as f:
        json.dump(meta, f, indent=4)
    print(f"📝 Run metadata saved to {output_path}")
