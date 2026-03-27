"""
Reproducibility Verification Script.
Runs training twice and asserts bit-exact constraint on the output model.
"""

import os
import sys
import hashlib
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "data" / "corner_model_v2_professional.pkl"
CMD = [sys.executable, str(PROJECT_ROOT / "src" / "main.py"), "--train", "1"]

def get_file_hash(path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def run_training(run_id):
    print(f"\n[Verify] Starting Training Run #{run_id}...")
    # Use specific environment variables if needed, here we rely on main.py hardcoded seed
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    # Captura output para não poluir demais, mas mostra erro se falhar
    result = subprocess.run(CMD, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding='utf-8', env=env)
    
    if result.returncode != 0:
        print(f"❌ Run #{run_id} Failed!")
        print(result.stderr)
        sys.exit(1)
        
    print(f"✅ Run #{run_id} Completed.")
    return get_file_hash(MODEL_PATH)

def main():
    print(f"🔍 Verifying Reproducibility (Target: {MODEL_PATH})")
    
    # Run 1
    if MODEL_PATH.exists():
        os.remove(MODEL_PATH)
    
    hash1 = run_training(1)
    print(f"   #1 Hash: {hash1}")
    
    # Run 2
    if MODEL_PATH.exists():
        os.remove(MODEL_PATH)
        
    hash2 = run_training(2)
    print(f"   #2 Hash: {hash2}")
    
    if hash1 == hash2:
        print("\n✅ SUCCESS: Bit-exact reproducibility achieved!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Models differ across runs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
