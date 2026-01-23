import sqlite3
import os

class Database:
    """
    Handles all persistent storage for the Integrity Monitor.
    Uses SQLite for lightweight, zero-config data management.
    """
    def __init__(self, db_path="data/monitor.db"):
        self.db_path = db_path
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._prepare_database()

    def _get_connection(self):
        """Internal helper for database connectivity."""
        return sqlite3.connect(self.db_path)

    def _prepare_database(self):
        """Initializes schema and applies necessary migrations."""
        schema = [
            '''CREATE TABLE IF NOT EXISTS ignore_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL
            )''',
            '''CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_name TEXT NOT NULL,
                status TEXT NOT NULL,
                actor TEXT,
                is_read INTEGER DEFAULT 0
            )''',
            '''CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )'''
        ]
        
        with self._get_connection() as conn:
            db = conn.cursor()
            for cmd in schema:
                db.execute(cmd)
            
            # Default Configuration
            defaults = [
                ("run_on_startup", "1"),
                ("last_directory", "")
            ]
            db.executemany('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', defaults)
            
            # Global Exclusion Defaults
            ignore_defaults = [('.git', 'directory'), ('__pycache__', 'directory'), ('.exe', 'extension')]
            db.executemany('INSERT OR IGNORE INTO ignore_list (pattern, type) VALUES (?, ?)', ignore_defaults)
            
            # Handling Schema Migrations
            try:
                db.execute('SELECT actor FROM alerts LIMIT 1')
            except sqlite3.OperationalError:
                db.execute('ALTER TABLE alerts ADD COLUMN actor TEXT')

            try:
                db.execute('SELECT is_read FROM alerts LIMIT 1')
            except sqlite3.OperationalError:
                db.execute('ALTER TABLE alerts ADD COLUMN is_read INTEGER DEFAULT 0')

    # --- Alert Management ---

    def add_alert(self, file_name, status, actor="Unknown"):
        with self._get_connection() as conn:
            conn.execute('INSERT INTO alerts (file_name, status, actor, is_read) VALUES (?, ?, ?, 0)', (file_name, status, actor))

    def get_alerts(self, limit=100, unread_only=False):
        query = 'SELECT timestamp, file_name, status, actor FROM alerts'
        if unread_only:
            query += ' WHERE is_read = 0'
        query += ' ORDER BY timestamp DESC LIMIT ?'
        
        with self._get_connection() as conn:
            return conn.execute(query, (limit,)).fetchall()

    def mark_alerts_as_read(self):
        with self._get_connection() as conn:
            conn.execute('UPDATE alerts SET is_read = 1 WHERE is_read = 0')

    def clear_alerts(self):
        with self._get_connection() as conn:
            conn.execute('DELETE FROM alerts')

    # --- Backup & Snapshot Tracking ---

    def add_backup(self, original_path, backup_path):
        with self._get_connection() as conn:
            conn.execute('INSERT INTO backups (original_path, backup_path) VALUES (?, ?)', (original_path, backup_path))

    def get_latest_backup(self, original_path):
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT backup_path FROM backups WHERE original_path = ? ORDER BY timestamp DESC LIMIT 1', 
                (original_path,)
            ).fetchone()
            return row[0] if row else None

    # --- System Settings ---

    def set_setting(self, key, value):
        with self._get_connection() as conn:
            conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))

    def get_setting(self, key, default="0"):
        with self._get_connection() as conn:
            row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
            return row[0] if row else default

    # --- Exclusions ---

    def add_ignore(self, pattern, p_type):
        try:
            with self._get_connection() as conn:
                conn.execute('INSERT INTO ignore_list (pattern, type) VALUES (?, ?)', (pattern, p_type))
                return True
        except sqlite3.IntegrityError:
            return False

    def remove_ignore(self, pattern):
        with self._get_connection() as conn:
            conn.execute('DELETE FROM ignore_list WHERE pattern = ?', (pattern,))

    def get_ignore_list(self):
        with self._get_connection() as conn:
            return conn.execute('SELECT pattern, type FROM ignore_list').fetchall()
