import flet as ft
from src.config import config
import os

class Settings(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.tiktok_username = ft.TextField(label="TikTok Username", value=config.tiktok_username or "")
        self.fb_page_id = ft.TextField(label="Facebook Page ID", value=config.facebook_page_id or "")
        self.fb_token = ft.TextField(label="Facebook Page Token", value=config.facebook_page_token or "", password=True, can_reveal_password=True)
        self.sheet_doc_id = ft.TextField(label="Google Sheet ID", value=config.tiktok_sheet_id or "")

    def build(self):
        return ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Text("Configuration", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.tiktok_username,
                    self.fb_page_id,
                    self.fb_token,
                    self.sheet_doc_id,
                    ft.Divider(),
                    ft.ElevatedButton("Save Settings", on_click=self.save_settings)
                ]
            )
        )

    def save_settings(self, e):
        # In a real app, this would write back to .env or a json config file
        # For now, we just show a snackbar
        self.page.snack_bar = ft.SnackBar(ft.Text("Settings saved (Simulated)! Restart app to apply."))
        self.page.snack_bar.open = True
        self.page.update()
