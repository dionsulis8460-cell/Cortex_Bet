
import shutil
import os
from datetime import datetime

def create_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    root_dir = os.getcwd()
    backup_dir = os.path.join(root_dir, 'backups', f'backup_pre_neural_{timestamp}')
    
    print(f"Creating backup at: {backup_dir}")
    
    # Dirs to exclude (heavy stuff)
    ignore_patterns = shutil.ignore_patterns('__pycache__', 'node_modules', '.next', '.git', 'venv', 'data')
    
    # Create valid backup
    try:
        if not os.path.exists(os.path.join(root_dir, 'backups')):
            os.makedirs(os.path.join(root_dir, 'backups'))
            
        shutil.copytree(
            os.path.join(root_dir, 'src'), 
            os.path.join(backup_dir, 'src'), 
            ignore=ignore_patterns
        )
        shutil.copytree(
            os.path.join(root_dir, 'web_app'), 
            os.path.join(backup_dir, 'web_app'), 
            ignore=ignore_patterns
        )
        shutil.copytree(
            os.path.join(root_dir, 'scripts'), 
            os.path.join(backup_dir, 'scripts'), 
            ignore=ignore_patterns
        )
        
        print("Backup completed successfully!")
        print(f"   Location: {backup_dir}")
        
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == "__main__":
    create_backup()
