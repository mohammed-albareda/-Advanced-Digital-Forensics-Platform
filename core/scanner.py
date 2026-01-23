import os
from core.hasher import calculate_hash

import os
from core.hasher import calculate_hash
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_directory(directory_path, ignore_list=None, progress_callback=None):
    """
    Scans a directory recursively using multi-threading for high performance.
    """
    file_hashes = {}
    ignore_list = ignore_list or []
    
    ignore_exts = tuple(p for p, t in ignore_list if t == 'extension')
    ignore_dirs = set(p for p, t in ignore_list if t == 'directory')
    ignore_files = set(p for p, t in ignore_list if t == 'file')

    # 1. Collect all valid files first (very fast)
    files_to_scan = []
    for root, dirs, files in os.walk(directory_path):
        # Prune ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file.endswith(ignore_exts) or file in ignore_files:
                continue
            files_to_scan.append(os.path.join(root, file))

    total_files = len(files_to_scan)
    if total_files == 0:
        return {}

    # 2. Hash files in parallel
    processed_count = 0
    # Use cpu_count * 2 or more for SSDs. 8-16 is usually good for I/O bound hashing.
    max_workers = min(32, (os.cpu_count() or 1) * 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(calculate_hash, f): f for f in files_to_scan}
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file_hash = future.result()
                if file_hash:
                    rel_path = os.path.relpath(file_path, directory_path)
                    file_hashes[rel_path] = file_hash
            except Exception:
                pass
            
            processed_count += 1
            # Update UI every 1% or every 10 files to reduce signal overhead
            if progress_callback:
                if processed_count % max(1, total_files // 100) == 0 or processed_count == total_files:
                    progress_callback(int((processed_count / total_files) * 100))
                
    return file_hashes
