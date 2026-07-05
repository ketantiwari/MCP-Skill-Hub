from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import reflex as rx

from dynamic_mcp_skill_hub.ui.common import ThemeState
from dynamic_mcp_skill_hub.ui import (
    portal_page,
    tools_page,
    activity_page,
    settings_page,
)

app = rx.App(
    theme=rx.theme(
        appearance=ThemeState.appearance,
        accent_color="sky",
        radius="large",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap",
    ],
)

# Pages are already registered via their decorators in the imported modules

