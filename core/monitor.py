import os
import psutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class IntegrityHandler(FileSystemEventHandler):
    def __init__(self, callback, db, ignore_dirs):
        self.callback = callback
        self.db = db
        self.ignore_dirs = ignore_dirs
        self._last_processed = {} # {path: (hash, timestamp)}
        self._cooldown = 1.5 # Seconds to ignore duplicate events for the same file

    def on_modified(self, event):
        if not event.is_directory:
            self._process_event(event, "🔴 Modified")

    def on_created(self, event):
        if not event.is_directory:
            self._process_event(event, "🟡 Created")

    def on_deleted(self, event):
        if not event.is_directory:
            self._process_event(event, "❌ Deleted")

    def _get_process_locking_file(self, target_path):
        """Attempts to identify which process is currently accessing the file."""
        try:
            target_path = os.path.normpath(target_path).lower()
            for proc in psutil.process_iter(['name', 'open_files']):
                try:
                    files = proc.info.get('open_files')
                    if files:
                        for f in files:
                            if os.path.normpath(f.path).lower() == target_path:
                                return proc.info['name']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return "System / Background"

    def _process_event(self, event, status):
        from core.hasher import calculate_hash

        # 1. Advanced Filtering (Temporary & Noise Files)
        filename = os.path.basename(event.src_path).lower()
        noise_extensions = ('.tmp', '.temp', '.lnk', '.ini', '.db-journal', '.lock', '.swp', '.bak')
        noise_prefixes = ('~', '.', 'tmp')
        
        if filename.startswith(noise_prefixes) or filename.endswith(noise_extensions) or '$' in filename:
            return

        # 2. Directory exclusion check
        path_parts = os.path.normpath(event.src_path).split(os.sep)
        if any(ignored in path_parts for ignored in self.ignore_dirs):
            return

        # 3. Small delay to allow the OS/App to finish the write operation
        time.sleep(0.3)

        # 4. Hash-based deduplication & Cooldown
        try:
            if os.path.exists(event.src_path):
                current_hash = calculate_hash(event.src_path)
                current_time = time.time()
                
                last_data = self._last_processed.get(event.src_path)
                if last_data:
                    last_hash, last_ts = last_data
                    if current_hash == last_hash or (current_time - last_ts < self._cooldown):
                        return 
                
                self._last_processed[event.src_path] = (current_hash, current_time)
            else:
                if event.src_path in self._last_processed:
                    del self._last_processed[event.src_path]
        except Exception:
            return 

        # 5. Forensic: Identify the Actor
        actor = self._get_process_locking_file(event.src_path)

        # Save to DB and Notify UI
        self.db.add_alert(filename, status, actor)
        self.callback(filename, status)

class RealTimeMonitor:
    def __init__(self, directory, callback, db, ignore_dirs=None):
        self.directory = directory
        self.callback = callback
        self.db = db
        self.ignore_dirs = ignore_dirs or []
        self.observer = Observer()

    def start(self):
        handler = IntegrityHandler(self.callback, self.db, self.ignore_dirs)
        self.observer.schedule(handler, self.directory, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
