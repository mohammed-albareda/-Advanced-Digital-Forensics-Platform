import os
import shutil
import sqlite3
from datetime import datetime

class BackupManager:
    def __init__(self, backup_dir="data/backups"):
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, file_path, original_root):
        """Creates a versioned backup of the file."""
        if not os.path.exists(file_path):
            return None
            
        rel_path = os.path.relpath(file_path, original_root)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create unique backup filename
        backup_filename = f"{timestamp}_{os.path.basename(file_path)}"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"Backup failed: {e}")
            return None

    def restore_file(self, backup_path, original_path):
        """Restores a file from backup."""
        try:
            shutil.copy2(backup_path, original_path)
            return True
        except Exception as e:
            print(f"Restore failed: {e}")
            return False
