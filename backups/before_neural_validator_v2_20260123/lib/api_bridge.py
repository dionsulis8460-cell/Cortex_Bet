"""
Dashboard API Bridge - Standalone Script
Called directly by Next.js API routes
"""
import sys
import os
import io

# 1. AGGRESSIVE OUTPUT SILENCING START
# Redirect stdout and stderr to capture ANY import-time prints (like DBManager debugs)
original_stdout = sys.stdout
original_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

import warnings
import json
import traceback

# Suppress warnings
warnings.filterwarnings('ignore')

# Set project root
project_root = r'C:\Users\OEM\Desktop\Cortex_Bet\Cortex_Bet'
sys.path.insert(0, project_root)
os.chdir(project_root)

# Get parameters from command line
# (We need to be careful reading args if we silenced stdout/stderr, but args are fine)
try:
    params = {
        'type': sys.argv[1] if len(sys.argv) > 1 else 'predictions',
        'date': sys.argv[2] if len(sys.argv) > 2 else 'today',
        'league': sys.argv[3] if len(sys.argv) > 3 else 'all',
        'status': sys.argv[4] if len(sys.argv) > 4 else 'all',
        'top7_only': sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False,
        'sort_by': sys.argv[6] if len(sys.argv) > 6 else 'confidence'
    }

    from web_app.lib.dashboard_data import get_dashboard_data
    
    # Get data
    data = get_dashboard_data(**params)
    
    # 2. RESTORE STDOUT FOR FINAL JSON OUTPUT
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    
    # Output as JSON (only this line will be stdout)
    print(json.dumps(data, ensure_ascii=False))
    
except Exception as e:
    # Restore stdout to print error JSON
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    
    # Return error as JSON
    error_response = {
        'error': str(e),
        'traceback': traceback.format_exc(),
        'type': 'python_error'
    }
    print(json.dumps(error_response))
    sys.exit(1)
