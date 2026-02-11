import flet as ft
from datetime import datetime
from src.services.minigame import MinigameModule

class Dashboard(ft.UserControl):
    def __init__(self, tiktok_service, facebook_service, aggregator):
        super().__init__()
        self.tiktok_service = tiktok_service
        self.facebook_service = facebook_service
        self.aggregator = aggregator
        self.minigame = MinigameModule()
        
        # Stats Controls
        self.txt_tt_viewers = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_tt_comments = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_fb_viewers = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        self.txt_fb_comments = ft.Text("0", size=30, weight=ft.FontWeight.BOLD)
        
        # Log Control
        self.log_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def build(self):
        return ft.Column(
            [
                # Stats Row 1
                ft.Row(
                    [
                        self._build_stat_card("TikTok Viewers", self.txt_tt_viewers, ft.colors.PINK_400),
                        self._build_stat_card("TikTok Comments", self.txt_tt_comments, ft.colors.PURPLE_400),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY
                ),
                ft.Container(height=10),
                # Stats Row 2
                ft.Row(
                    [
                        self._build_stat_card("FB Viewers", self.txt_fb_viewers, ft.colors.BLUE_400),
                        self._build_stat_card("FB Comments", self.txt_fb_comments, ft.colors.BLUE_600),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY
                ),
                ft.Divider(height=20),
                
                # Control Buttons
                ft.Row(
                    [
                        ft.ElevatedButton("Start TikTok", icon=ft.icons.PLAY_ARROW, on_click=lambda _: self.tiktok_service.start(), bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE),
                        ft.ElevatedButton("Stop TikTok", icon=ft.icons.STOP, on_click=lambda _: self.tiktok_service.stop(), bgcolor=ft.colors.RED_600, color=ft.colors.WHITE),
                        ft.Container(width=10),
                        ft.ElevatedButton("Start Facebook", icon=ft.icons.PLAY_ARROW, on_click=lambda _: self.facebook_service.start(), bgcolor=ft.colors.BLUE_600, color=ft.colors.WHITE),
                        ft.ElevatedButton("Stop Facebook", icon=ft.icons.STOP, on_click=lambda _: self.facebook_service.stop(), bgcolor=ft.colors.RED_800, color=ft.colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Divider(height=20),

                # Minigame Section
                ft.Text("Minigame", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Pick Winner", on_click=self.pick_winner),
                        ft.ElevatedButton("Reset List", on_click=lambda _: self.minigame.reset()),
                    ],
                ),
                
                # Export Section (New Row to avoid overflow)
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.ElevatedButton("Export CSV", on_click=lambda _: self.export_data("csv"), icon=ft.icons.DOWNLOAD),
                        ft.ElevatedButton("Export Excel", on_click=lambda _: self.export_data("excel"), icon=ft.icons.TABLE_VIEW),
                        ft.ElevatedButton("Export to Sheet", on_click=lambda _: self.export_data("sheet", "sheet"), icon=ft.icons.CLOUD_UPLOAD, bgcolor=ft.colors.ORANGE_400),
                    ],
                    wrap=True # Allow wrapping if needed
                ),
                ft.Divider(height=20),
                
                # Log Section
                ft.Text("Live Event Log", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.log_view,
                    expand=True,
                    bgcolor=ft.colors.BLACK12,
                    border_radius=10,
                    padding=10
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO # Enable scrolling for the whole dashboard if height is small
        )

    def _build_stat_card(self, title, value_control, color):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=14, color=ft.colors.GREY_400),
                    value_control
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=ft.colors.SURFACE_VARIANT,
            padding=20,
            border_radius=10,
            width=200,
            border=ft.border.all(1, color)
        )

    def handle_update(self, event_type, data):
        """Updates the UI based on events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if event_type == "comment":
            # ... (TikTok comment logic)
            current = int(self.txt_tt_comments.value)
            self.txt_tt_comments.value = str(current + 1)
            self.log_view.controls.append(ft.Row([ft.Text(f"[{timestamp}] TT", color=ft.colors.PINK_400, size=12), ft.Text(f"{data['user']}:", weight=ft.FontWeight.BOLD), ft.Text(data['comment'])]))
            self.aggregator.add_event("tiktok", "comment", data)
            self.minigame.add_participant(data['user'])

        elif event_type == "gift":
            # ... (TikTok gift logic)
            self.log_view.controls.append(ft.Row([ft.Text(f"[{timestamp}] GIFT", color=ft.colors.YELLOW_400, size=12), ft.Text(f"{data['user']} sent {data['gift']} x{data['count']}", weight=ft.FontWeight.BOLD, color=ft.colors.YELLOW)]))
            self.aggregator.add_event("tiktok", "gift", data)

        elif event_type == "status":
            self.log_view.controls.append(ft.Text(f"[{timestamp}] SYSTEM: {data['status']}", color=ft.colors.GREEN))

        elif event_type == "fb_comment":
            current = int(self.txt_fb_comments.value)
            self.txt_fb_comments.value = str(current + 1)
            self.log_view.controls.append(ft.Row([ft.Text(f"[{timestamp}] FB", color=ft.colors.BLUE_400, size=12), ft.Text(f"{data['user']}:", weight=ft.FontWeight.BOLD), ft.Text(data['comment'])]))
            self.aggregator.add_event("facebook", "fb_comment", data)

        elif event_type == "fb_viewers":
            self.txt_fb_viewers.value = str(data["count"])
        
        elif event_type == "fb_reaction":
            # Just log reactions for now, or could have a counter
            self.log_view.controls.append(ft.Row([ft.Text(f"[{timestamp}] FB React", color=ft.colors.BLUE_200, size=12), ft.Text(f"{data['user']} reacted {data['type']}")] ) )
            self.aggregator.add_event("facebook", "reaction", data)

        self.update()

    def pick_winner(self, e):
        winner = self.minigame.pick_winner()
        if winner:
            self.log_view.controls.append(
                ft.Row([
                    ft.Text("🎉 WINNER:", color=ft.colors.YELLOW, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{winner} has won the minigame!", size=16, color=ft.colors.GREEN)
                ])
            )
            dialog = ft.AlertDialog(
                title=ft.Text("🎉 Winner!"),
                content=ft.Text(f"The winner is: {winner}"),
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
            self.update()
        else:
             self.page.snack_bar = ft.SnackBar(ft.Text("No participants yet!"))
             self.page.snack_bar.open = True
             self.page.update()

    def export_data(self, format="csv", destination="local"):
        result = self.aggregator.export_session_data(format, destination)
        if result:
            msg = f"Exported to {result}" if destination == "local" else "Uploaded to Google Sheet 'Report' tab!"
            self.page.snack_bar = ft.SnackBar(ft.Text(msg))
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("Export failed! Check logs."))
        self.page.snack_bar.open = True
        self.page.update()
