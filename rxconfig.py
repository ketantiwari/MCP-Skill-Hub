import os
import reflex as rx

from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = "workspace"

config = rx.Config(
    app_name="app",
    frontend_port=3030,
    backend_port=8030,
    disable_plugins=[rx.plugins.SitemapPlugin],
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="inherit",
                has_background=True,
                radius="large",
                accent_color="cyan",
            )
        )
    ]
)
