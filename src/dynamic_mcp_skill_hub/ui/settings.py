from __future__ import annotations

import reflex as rx
from dynamic_mcp_skill_hub.ui.common import (
    layout_wrapper,
    content_panel,
    ThemeState,
    THEME_TEXT,
    THEME_SUBTEXT,
    THEME_MUTED,
    THEME_BORDER,
    THEME_INPUT_BG,
    THEME_CARD_BG,
)


class SettingsState(rx.State):
    gemini_key_configured: bool = False
    groq_key_configured: bool = False
    nvidia_key_configured: bool = False
    google_model: str = "-"
    groq_model: str = "-"
    deepseek_model: str = "-"
    sandbox_mode: str = "-"
    port: int = 3030

    @rx.event
    def load_settings(self) -> None:
        from dynamic_mcp_skill_hub.config import get_settings
        settings = get_settings()
        self.gemini_key_configured = bool(settings.gemini_api_key)
        self.groq_key_configured = bool(settings.groq_api_key)
        self.nvidia_key_configured = bool(settings.nvidia_api_key)
        self.google_model = settings.google_model
        self.groq_model = settings.groq_model
        self.deepseek_model = settings.nvidia_deepseek_model
        self.sandbox_mode = settings.sandbox_mode
        self.port = settings.port


def api_key_row(name: str, configured: rx.Var[bool]) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(name, font_weight="600", color=THEME_TEXT, font_size="0.95rem"),
            rx.text(
                rx.cond(configured, "API Key Configured", "API Key Missing"),
                font_size="0.8rem",
                color=rx.cond(configured, "#10b981", "#ef4444"),
            ),
            align="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.cond(
            configured,
            rx.icon("circle_check", color="#10b981", size=20),
            rx.icon("circle_x", color="#ef4444", size=20),
        ),
        width="100%",
        padding="0.8rem 1rem",
        border_radius="14px",
        bg="rgba(148, 163, 184, 0.05)",
        border=f"1px solid {THEME_BORDER}",
        align="center",
    )


def config_value_row(label: str, value: rx.Var[str]) -> rx.Component:
    return rx.hstack(
        rx.text(label, color=THEME_MUTED, font_size="0.9rem"),
        rx.spacer(),
        rx.text(value, font_weight="600", color=THEME_TEXT, font_size="0.9rem"),
        width="100%",
        padding="0.8rem 1rem",
        border_radius="14px",
        bg="rgba(148, 163, 184, 0.05)",
        border=f"1px solid {THEME_BORDER}",
        align="center",
    )


@rx.page(route="/settings", title="Settings & Theme - Dynamic MCP Skill Hub", on_load=SettingsState.load_settings)
def settings_page() -> rx.Component:
    return layout_wrapper(
        "Settings",
        "/settings",
        rx.grid(
            # Column 1: Appearance & Theme
            content_panel(
                "Theme Mode",
                "Choose how the application dashboard looks",
                rx.vstack(
                    rx.text(
                        "Appearance",
                        font_size="0.9rem",
                        font_weight="600",
                        color=THEME_TEXT,
                    ),
                    rx.hstack(
                        rx.button(
                            rx.hstack(
                                rx.icon("sun", size=16),
                                rx.text("Light"),
                                align="center",
                                spacing="2",
                            ),
                            on_click=ThemeState.select_theme("light"),
                            bg=rx.cond(ThemeState.appearance == "light", "#0ea5e9", "transparent"),
                            color=rx.cond(ThemeState.appearance == "light", "#ffffff", THEME_TEXT),
                            border=f"1px solid {THEME_BORDER}",
                            border_radius="12px",
                            flex="1",
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon("monitor", size=16),
                                rx.text("Auto"),
                                align="center",
                                spacing="2",
                            ),
                            on_click=ThemeState.select_theme("inherit"),
                            bg=rx.cond(ThemeState.appearance == "inherit", "#0ea5e9", "transparent"),
                            color=rx.cond(ThemeState.appearance == "inherit", "#ffffff", THEME_TEXT),
                            border=f"1px solid {THEME_BORDER}",
                            border_radius="12px",
                            flex="1",
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon("moon", size=16),
                                rx.text("Dark"),
                                align="center",
                                spacing="2",
                            ),
                            on_click=ThemeState.select_theme("dark"),
                            bg=rx.cond(ThemeState.appearance == "dark", "#0ea5e9", "transparent"),
                            color=rx.cond(ThemeState.appearance == "dark", "#ffffff", THEME_TEXT),
                            border=f"1px solid {THEME_BORDER}",
                            border_radius="12px",
                            flex="1",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    spacing="3",
                    align="stretch",
                    width="100%",
                ),
            ),
            # Column 2: API Keys Status
            content_panel(
                "API Credentials",
                "Status of external model integrations",
                rx.vstack(
                    api_key_row("Google Gemini", SettingsState.gemini_key_configured),
                    api_key_row("Groq Console", SettingsState.groq_key_configured),
                    api_key_row("NVIDIA NIM (DeepSeek)", SettingsState.nvidia_key_configured),
                    spacing="3",
                    align="stretch",
                    width="100%",
                ),
            ),
            # Column 3: Platform Settings
            content_panel(
                "Platform Specs",
                "Model configurations and execution environments",
                rx.vstack(
                    config_value_row("Google Model", SettingsState.google_model),
                    config_value_row("Groq Model", SettingsState.groq_model),
                    config_value_row("DeepSeek Model", SettingsState.deepseek_model),
                    config_value_row("Sandbox Environment", SettingsState.sandbox_mode),
                    config_value_row("Port", SettingsState.port.to(str)),
                    spacing="3",
                    align="stretch",
                    width="100%",
                ),
            ),
            template_columns="1fr 1fr 1fr",
            gap="1.5rem",
            width="100%",
        ),
    )
