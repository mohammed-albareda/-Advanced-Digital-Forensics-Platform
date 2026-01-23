import hashlib

def calculate_hash(file_path, algorithm='sha256'):
    """Calculates the hash of a file."""
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""): 
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None
