import sys
import os
import flet as ft

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    # Start the Flet application
    ft.app(target=main)
