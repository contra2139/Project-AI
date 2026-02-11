import flet as ft
import matplotlib
import matplotlib.pyplot as plt
from flet.matplotlib_chart import MatplotlibChart

matplotlib.use("svg")

class Analytics(ft.UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        return ft.Container(
            padding=20,
            content=ft.Column(
                [
                    ft.Text("Live Analytics", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("Viewer Trend (Mock Data)", size=16),
                    self._build_chart(),
                    ft.Divider(),
                    ft.Text("Comment Distribution", size=16),
                    # Additional charts can be added here
                ]
            )
        )

    def _build_chart(self):
        # Create a simple mock chart
        fig, ax = plt.subplots()
        x = [1, 2, 3, 4, 5]
        y = [100, 150, 200, 180, 250]
        ax.plot(x, y)
        ax.set_xlabel("Time (mins)")
        ax.set_ylabel("Viewers")
        ax.set_title("Real-time Viewers")
        
        return MatplotlibChart(fig, expand=True)
