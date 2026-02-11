import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft
from src.ui.main_window import MainWindow
from src.config import config

def main(page: ft.Page):
    app = MainWindow(page)
    # Ensure aggregator is started if needed here or in MainWindow
    app.aggregator.start()

if __name__ == "__main__":
    ft.app(target=main)
