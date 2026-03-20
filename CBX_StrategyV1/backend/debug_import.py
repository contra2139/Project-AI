import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app.telegram.handlers...")
    from app.telegram import handlers
    print("Import successful!")
except Exception as e:
    print("Import failed!")
    import traceback
    traceback.print_exc()
