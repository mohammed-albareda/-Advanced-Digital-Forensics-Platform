from PIL import Image
import os

png_path = r"C:\Users\Elite\.gemini\antigravity\brain\e6d42f3e-d9b0-471b-b03b-3e33b4d77ec8\app_icon_design_1768339681527.png"
ico_path = r"c:\Users\Elite\Desktop\file_integraity_checker\assets\icon.ico"
png_assets_path = r"c:\Users\Elite\Desktop\file_integraity_checker\assets\icon.png"

# Load image
img = Image.open(png_path)

# Save as PNG in assets
img.save(png_assets_path)

# Save as ICO (standard sizes)
img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print(f"Icon converted and saved to {ico_path}")
