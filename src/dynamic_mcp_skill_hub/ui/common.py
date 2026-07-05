from __future__ import annotations

import reflex as rx

# ─── Dynamic Theme Configuration ──────────────────────────────────────────────
class ThemeState(rx.State):
    appearance: str = rx.LocalStorage("inherit")  # "light", "dark", "inherit" (auto)

    def select_theme(self, mode: str) -> None:
        self.appearance = mode


def dynamic_color(light_val: str, dark_val: str) -> rx.Component:
    return rx.cond(
        ThemeState.appearance == "light",
        light_val,
        rx.cond(
            ThemeState.appearance == "dark",
            dark_val,
            rx.color_mode_cond(light=light_val, dark=dark_val)
        )
    )


# ─── Dynamic Semantic Style Tokens ────────────────────────────────────────────
THEME_BG = dynamic_color("#f8fafc", "#020617")  # slate-50 / slate-950
THEME_HEADER_BG = dynamic_color("rgba(255, 255, 255, 0.8)", "rgba(15, 23, 42, 0.72)")
THEME_CARD_BG = dynamic_color("#ffffff", "rgba(2, 6, 23, 0.52)")  # Pure white card in light mode
THEME_BORDER = dynamic_color("rgba(15, 23, 42, 0.08)", "rgba(148, 163, 184, 0.14)")  # Soft light-mode border
THEME_TEXT = dynamic_color("#0f172a", "#f8fafc")  # slate-900 / slate-50
THEME_SUBTEXT = dynamic_color("#475569", "#cbd5e1")  # slate-600 / slate-300
THEME_MUTED = dynamic_color("#64748b", "#94a3b8")  # slate-500 / slate-400
THEME_INPUT_BG = dynamic_color("#f1f5f9", "rgba(2, 6, 23, 0.68)")  # Off-white inputs in light mode
THEME_PANEL_BG = dynamic_color("#ffffff", "#090d16")
THEME_SHADOW = dynamic_color("0 8px 30px rgba(15, 23, 42, 0.04)", "0 10px 40px rgba(0, 0, 0, 0.12)")


# ─── Shared UI Helpers ────────────────────────────────────────────────────────
def nav_link(label: str, path: str, current_path: str) -> rx.Component:
    active = path == current_path
    return rx.link(
        rx.text(
            label,
            font_size="0.9rem",
            font_weight="600" if active else "500",
            color=rx.cond(active, "#0ea5e9", THEME_MUTED),
            transition="all 0.2s ease",
            _hover={"color": "#0ea5e9"},
            font_family="Plus Jakarta Sans",
        ),
        href=path,
        text_decoration="none",
    )


def header_theme_icon(icon_name: str, mode: str) -> rx.Component:
    """A small icon button for selecting a theme mode from the header."""
    active = ThemeState.appearance == mode
    return rx.icon_button(
        rx.icon(icon_name, size=14),
        on_click=ThemeState.select_theme(mode),
        size="2",
        variant=rx.cond(active, "solid", "ghost"),
        color_scheme="sky" if mode != "dark" else "indigo",
        bg=rx.cond(active, "#0ea5e9", "transparent"),
        color=rx.cond(active, "#ffffff", THEME_MUTED),
        _hover={
            "bg": rx.cond(active, "#0ea5e9", "rgba(14, 165, 233, 0.08)"),
            "color": "#0ea5e9",
            "cursor": "pointer",
        },
        border_radius="8px",
        transition="all 0.15s ease",
        width="1.8rem",
        height="1.8rem",
    )


def header_theme_switcher() -> rx.Component:
    """A compact, border-wrapped switcher for selecting theme modes."""
    return rx.hstack(
        header_theme_icon("sun", "light"),
        header_theme_icon("monitor", "inherit"),
        header_theme_icon("moon", "dark"),
        spacing="1",
        padding="2px",
        border_radius="10px",
        bg=dynamic_color("rgba(14, 165, 233, 0.03)", "rgba(14, 165, 233, 0.06)"),
        border=f"1px solid {THEME_BORDER}",
        align="center",
    )


def layout_wrapper(title: str, current_path: str, *children: rx.Component) -> rx.Component:
    """A standard layout containing the top navigation header and consistent background wrappers."""
    return rx.theme(
        rx.box(
            rx.box(
                position="absolute",
                inset="0",
                bg=dynamic_color(
                    "radial-gradient(ellipse at top, rgba(14, 165, 233, 0.06), transparent)",
                    "radial-gradient(ellipse at top, rgba(2, 6, 23, 0.95), transparent)",
                ),
                z_index="0",
            ),
            rx.vstack(
                # Top Navigation Header
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="10px",
                                height="10px",
                                border_radius="999px",
                                bg="#0ea5e9",
                            ),
                            rx.text(
                                "Dynamic MCP Skill Hub",
                                font_size="1.1rem",
                                font_weight="700",
                                color=THEME_TEXT,
                                font_family="Space Grotesk",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.hstack(
                            nav_link("Chat Portal", "/", current_path),
                            nav_link("Tools Manager", "/tools", current_path),
                            nav_link("Activity Logs", "/activity", current_path),
                            nav_link("Settings", "/settings", current_path),
                            spacing="6",
                            align="center",
                        ),
                        rx.hstack(
                            header_theme_switcher(),
                            rx.box(
                                rx.text(
                                    title,
                                    font_size="0.75rem",
                                    font_weight="700",
                                    color=dynamic_color("#0284c7", "#38bdf8"),
                                    font_family="Space Grotesk",
                                    text_transform="uppercase",
                                    letter_spacing="0.05em",
                                ),
                                bg=dynamic_color("rgba(14, 165, 233, 0.08)", "rgba(14, 165, 233, 0.18)"),
                                border=f"1px solid {dynamic_color('rgba(14, 165, 233, 0.15)', 'rgba(14, 165, 233, 0.3)')}",
                                padding="0.25rem 0.75rem",
                                border_radius="999px",
                            ),
                            spacing="3",
                            align="center",
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    padding="1rem 2rem",
                    border_radius="20px",
                    bg=THEME_HEADER_BG,
                    border=f"1px solid {THEME_BORDER}",
                    backdrop_filter="blur(12px)",
                    width="100%",
                    box_shadow=THEME_SHADOW,
                ),
                # Content Area
                rx.box(
                    *children,
                    width="100%",
                    padding_top="0.5rem",
                ),
                spacing="5",
                padding="1.5rem",
                width="min(1540px, calc(100% - 1rem))",
                margin="0 auto",
                align="stretch",
                position="relative",
                z_index="1",
            ),
            position="relative",
            min_height="100vh",
            overflow="hidden",
            bg=THEME_BG,
            font_family="Plus Jakarta Sans",
        ),
        appearance=ThemeState.appearance,
        accent_color="sky",
        radius="large",
    )


def content_panel(title: str, subtitle: str, *children: rx.Component) -> rx.Component:
    """A standard panel wrapping elements with dynamic theme borders and backgrounds."""
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.text(
                    title,
                    font_size="0.75rem",
                    letter_spacing="0.12em",
                    text_transform="uppercase",
                    color=THEME_MUTED,
                    font_weight="700",
                    font_family="Space Grotesk",
                ),
                rx.text(
                    subtitle, 
                    color=THEME_SUBTEXT, 
                    font_size="0.9rem",
                    font_family="Plus Jakarta Sans",
                ),
                align="start",
                spacing="1",
            ),
            *children,
            spacing="4",
            align="stretch",
        ),
        padding="1.5rem",
        border_radius="24px",
        bg=THEME_CARD_BG,
        border=f"1px solid {THEME_BORDER}",
        box_shadow=THEME_SHADOW,
        backdrop_filter="blur(8px)",
        width="100%",
    )


def premium_button(label: str, icon_name: str, on_click, **props) -> rx.Component:
    """A custom styled primary button with high-contrast, premium styling for both modes."""
    return rx.button(
        rx.hstack(
            rx.icon(icon_name, size=15),
            rx.text(label),
            align="center",
            spacing="2",
        ),
        on_click=on_click,
        bg=dynamic_color("#0ea5e9", "rgba(14, 165, 233, 0.15)"),
        color=dynamic_color("#ffffff", "#38bdf8"),
        border=dynamic_color("none", "1px solid rgba(14, 165, 233, 0.25)"),
        _hover={
            "bg": dynamic_color("#0284c7", "rgba(14, 165, 233, 0.25)"),
            "cursor": "pointer",
        },
        transition="all 0.15s ease",
        font_family="Plus Jakarta Sans",
        font_weight="600",
        border_radius="12px",
        height="2.3rem",
        **props
    )


def custom_badge(label: str, color_type: str = "blue") -> rx.Component:
    """A customized pill badge that dynamically maintains excellent contrast."""
    if color_type == "green":
        text_color = dynamic_color("#16a34a", "#4ade80")
        bg_color = dynamic_color("rgba(22, 163, 74, 0.08)", "rgba(34, 197, 94, 0.18)")
        border_color = dynamic_color("rgba(22, 163, 74, 0.15)", "rgba(34, 197, 94, 0.3)")
    elif color_type == "red":
        text_color = dynamic_color("#dc2626", "#f87171")
        bg_color = dynamic_color("rgba(220, 38, 38, 0.08)", "rgba(239, 68, 68, 0.18)")
        border_color = dynamic_color("rgba(220, 38, 38, 0.15)", "rgba(239, 68, 68, 0.3)")
    else:  # blue/sky
        text_color = dynamic_color("#0284c7", "#38bdf8")
        bg_color = dynamic_color("rgba(14, 165, 233, 0.08)", "rgba(14, 165, 233, 0.18)")
        border_color = dynamic_color("rgba(14, 165, 233, 0.15)", "rgba(14, 165, 233, 0.3)")
        
    return rx.box(
        rx.text(
            label,
            font_size="0.75rem",
            font_weight="700",
            color=text_color,
            font_family="Space Grotesk",
        ),
        bg=bg_color,
        border=f"1px solid {border_color}",
        padding="0.2rem 0.60rem",
        border_radius="8px",
        display="inline-flex",
        align_items="center",
        justify_content="center",
    )
