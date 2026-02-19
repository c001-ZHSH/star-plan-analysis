import PyInstaller.__main__
import sys
import os

# Determine separator for add-data
# Windows uses ';', Mac/Linux uses ':'
sep = ';' if sys.platform.startswith('win') else ':'

print(f"Building for platform: {sys.platform}")
print(f"Using separator: {sep}")

PyInstaller.__main__.run([
    'backend/app.py',
    '--name=StarPlanAnalysis',
    '--onefile',
    '--clean',
    f'--add-data=frontend{sep}frontend',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=csv',
    '--hidden-import=_csv',
])

print("Build complete!")
