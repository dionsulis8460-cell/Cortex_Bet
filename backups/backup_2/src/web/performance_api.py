"""
Performance API Entry Point

Standalone script to be called from the web API
"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.analysis.performance_calculator import get_performance_data
    
    # Get arguments
    from_date = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != 'None' else None
    to_date = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != 'None' else None
    
    # Get data
    data = get_performance_data(from_date, to_date)
    
    # Output JSON
    print(json.dumps(data))
    
except Exception as e:
    print(json.dumps({
        'error': str(e),
        'type': type(e).__name__
    }), file=sys.stderr)
    sys.exit(1)
