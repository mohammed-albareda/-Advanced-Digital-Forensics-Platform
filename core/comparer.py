def compare_scans(baseline, current_scan):
    """
    Compares current scan against baseline.
    Returns a list of dictionaries with status.
    """
    results = []
    
    # Check for modifications and deletions
    for file_path, baseline_hash in baseline.items():
        if file_path in current_scan:
            if current_scan[file_path] != baseline_hash:
                results.append({
                    "file": file_path,
                    "status": "🔴 Modified",
                    "details": "Hash changed"
                })
            else:
                # Optional: tracking unchanged files
                # results.append({"file": file_path, "status": "🟢 Unchanged", "details": ""})
                pass
        else:
            results.append({
                "file": file_path,
                "status": "❌ Deleted",
                "details": "Missing file"
            })
            
    # Check for new files
    for file_path in current_scan:
        if file_path not in baseline:
            results.append({
                "file": file_path,
                "status": "🟡 New",
                "details": "New file detected"
            })
            
    return results
