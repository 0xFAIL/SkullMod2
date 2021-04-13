# SkullMod 2, Unofficial modding tool for Skullgirls

# How to build
Get Python 3.9+
Make sure the Python exe is available in PATH (should be by default after installing Python) or create a venv
Only tested on Windows 10, if you want to build it on Linux or Mac OS remove the winreg import and everything associated

# Install dependency
pip install wxpython

# Run it directly
Execute SkullMod2.py with Python

# ... or make an exe out the package
pip install pyinstaller
Run in the same directory as SkullMod2.py:
pyinstaller --windowed --onefile --icon app.ico SkullMod2.py
Resulting exe file will be in the dist directory