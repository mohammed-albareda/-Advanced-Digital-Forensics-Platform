import os
import sys
import winreg

def set_run_at_startup(enabled=True):
    """Adds/Removes the app from Windows startup registry."""
    app_name = "FileIntegrityMonitor"
    
    # Get path of the current executable/script
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        app_path = os.path.abspath(sys.argv[0])
        app_path = f'"{sys.executable}" "{app_path}"'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Startup error: {e}")
        return False
