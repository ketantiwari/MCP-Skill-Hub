from __future__ import annotations

import json
from pathlib import Path
import reflex as rx
from dynamic_mcp_skill_hub.ui.common import (
    layout_wrapper,
    content_panel,
    THEME_TEXT,
    THEME_SUBTEXT,
    THEME_MUTED,
    THEME_BORDER,
    custom_badge,
)


class ActivityState(rx.State):
    logs: list[dict[str, str]] = []

    @rx.event
    def load_logs(self) -> None:
        from dynamic_mcp_skill_hub.config import get_settings
        settings = get_settings()
        log_file = Path(settings.log_dir) / "audit.jsonl"
        
        parsed_logs = []
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    # Read the last 50 lines
                    lines = f.readlines()
                    for line in reversed(lines[-50:]):
                        line = line.strip()
                        if line:
                            parsed_logs.append(json.loads(line))
            except Exception:
                pass
                
        # If no logs exist, provide a skeleton
        if not parsed_logs:
            self.logs = []
        else:
            self.logs = [
                {
                    "timestamp": str(log.get("timestamp", "-")),
                    "query": str(log.get("query", "-")),
                    "intent": str(log.get("intent", "unknown")),
                    "status": str(log.get("status", "unknown")),
                    "tool_name": str(log.get("tool_name", "-")),
                    "version": str(log.get("version", "-")),
                }
                for log in parsed_logs
            ]


def audit_table_row(log: dict[str, str]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(log["timestamp"], font_size="0.84rem", color=THEME_MUTED),
        rx.table.cell(log["query"], font_size="0.86rem", color=THEME_TEXT),
        rx.table.cell(
            custom_badge(log["intent"], "blue")
        ),
        rx.table.cell(
            rx.cond(
                log["status"] == "published",
                custom_badge(log["status"], "green"),
                custom_badge(log["status"], "red"),
            )
        ),
        rx.table.cell(log["tool_name"], font_size="0.86rem", color=THEME_TEXT, font_weight="600"),
        rx.table.cell(log["version"], font_size="0.84rem", color=THEME_MUTED),
    )


@rx.page(route="/activity", title="Activity Logs - Dynamic MCP Skill Hub", on_load=ActivityState.load_logs)
def activity_page() -> rx.Component:
    return layout_wrapper(
        "Activity Logs",
        "/activity",
        content_panel(
            "Audit Logs",
            "Telemetry records of recent tool building operations and intake actions",
            rx.cond(
                ActivityState.logs.length() == 0,
                rx.center(
                    rx.vstack(
                        rx.icon("archive", size=48, color=THEME_MUTED),
                        rx.text("No audit log entries found.", color=THEME_MUTED, font_size="1rem"),
                        spacing="3",
                        align="center",
                    ),
                    padding="4rem",
                    width="100%",
                ),
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Timestamp"),
                                rx.table.column_header_cell("User Query"),
                                rx.table.column_header_cell("Intent"),
                                rx.table.column_header_cell("Status"),
                                rx.table.column_header_cell("Tool Built"),
                                rx.table.column_header_cell("Version"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                ActivityState.logs,
                                audit_table_row,
                            )
                        ),
                        width="100%",
                        variant="ghost",
                    ),
                    overflow_x="auto",
                    width="100%",
                    border_radius="18px",
                    border=f"1px solid {THEME_BORDER}",
                ),
            ),
        ),
    )
