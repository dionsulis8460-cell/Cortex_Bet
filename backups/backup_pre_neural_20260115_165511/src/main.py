"""
Módulo Principal - Sistema de Previsão de Escanteios com Machine Learning.
Cortex V2.1 - Entry Point.
"""

import sys
import os

# Add project root to path (one level up from src)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.interface.cli import run_cli

if __name__ == "__main__":
    run_cli()