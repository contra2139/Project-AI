import flet as ft
from src.ui.dashboard import Dashboard
from src.ui.settings import Settings
from src.ui.analytics import Analytics
from src.services.data_aggregator import DataAggregator
from src.services.tiktok_client import TikTokService
from src.services.facebook_client import FacebookService
from src.services.sheet_manager import GoogleSheetClient

class MainWindow:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Live Stream Tracker Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window_min_width = 1000
        self.page.window_min_height = 700

        # Initialize Services
        self.sheet_client = GoogleSheetClient()
        self.aggregator = DataAggregator(self.sheet_client)
        self.tiktok_service = TikTokService(update_callback=self.on_data_update)
        self.facebook_service = FacebookService(update_callback=self.on_data_update)

        # UI Components
        self.dashboard = Dashboard(
            self.tiktok_service, 
            self.facebook_service,
            self.aggregator
        )
        self.settings_view = Settings()
        self.analytics_view = Analytics()
        
        # Container for changing content
        self.content_area = ft.Container(content=self.dashboard, expand=True, padding=20)
        
        self.build_ui()

    def build_ui(self):
        self.page.add(
            ft.Row(
                [
                    self._build_sidebar(),
                    ft.VerticalDivider(width=1),
                    self.content_area
                ],
                expand=True
            )
        )

    def _build_sidebar(self):
        return ft.Container(
            width=180,
            expand=True,
            bgcolor=ft.colors.SURFACE_VARIANT,
            padding=20,
            content=ft.Column(
                [
                    ft.Text("Live Tracker", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.NavigationRail(
                        selected_index=0,
                        destinations=[
                            ft.NavigationRailDestination(
                                icon=ft.icons.DASHBOARD, 
                                label="Dashboard"
                            ),
                            ft.NavigationRailDestination(
                                icon=ft.icons.SETTINGS, 
                                label="Settings"
                            ),
                            ft.NavigationRailDestination(
                                icon=ft.icons.ANALYTICS, 
                                label="Reports"
                            ),
                        ],
                        on_change=self.on_nav_change,
                        expand=True
                    ),
                    ft.ElevatedButton("Exit App", on_click=lambda _: self.page.window_close())
                ],
                expand=True
            )
        )

    def on_nav_change(self, e):
        index = e.control.selected_index
        if index == 0:
            self.content_area.content = self.dashboard
        elif index == 1:
            self.content_area.content = self.settings_view
        elif index == 2:
            self.content_area.content = self.analytics_view
        self.content_area.update()

    def on_data_update(self, event_type, data):
        """Callback from services to update UI"""
        # Dispatch to dashboard to update stats/logs
        self.dashboard.handle_update(event_type, data)
