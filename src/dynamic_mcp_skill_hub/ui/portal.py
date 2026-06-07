from __future__ import annotations

import json
from typing import Any

import reflex as rx

from dynamic_mcp_skill_hub.interceptor import QueryInterceptor

_ACTIVE_TASKS = {}


class PortalState(rx.State):
    query_text: str = rx.LocalStorage("Create a simple weather lookup tool")
    status_text: str = rx.LocalStorage("Ready")
    tool_name: str = rx.LocalStorage("-")
    version_text: str = rx.LocalStorage("-")
    tool_path: str = rx.LocalStorage("-")
    result_json: str = rx.LocalStorage("")
    history_json: str = rx.LocalStorage("[]")
    busy: bool = False
    audit_logs: list[dict[str, Any]] = []

    @rx.event
    def update_query(self, value: str) -> None:
        self.query_text = value

    def _save_last_run(self) -> None:
        from pathlib import Path
        import json
        last_run_file = Path("workspace/logs/last_run.json")
        last_run_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "result_json": self.result_json,
            "status_text": self.status_text,
            "tool_name": self.tool_name,
            "version_text": self.version_text,
            "tool_path": self.tool_path,
            "query_text": self.query_text,
            "history_json": self.history_json,
        }
        try:
            last_run_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _load_last_run(self) -> None:
        from pathlib import Path
        import json
        last_run_file = Path("workspace/logs/last_run.json")
        if last_run_file.exists():
            try:
                data = json.loads(last_run_file.read_text(encoding="utf-8"))
                self.result_json = data.get("result_json", "")
                self.status_text = data.get("status_text", "Ready")
                self.tool_name = data.get("tool_name", "-")
                self.version_text = data.get("version_text", "-")
                self.tool_path = data.get("tool_path", "-")
                self.query_text = data.get("query_text", "Create a simple weather lookup tool")
                self.history_json = data.get("history_json", "[]")
            except Exception:
                pass

    @rx.event
    def load_audit_logs(self) -> None:
        self._load_last_run()
        from pathlib import Path
        import json
        log_file = Path("workspace/logs/audit.jsonl")
        if not log_file.exists():
            self.audit_logs = []
            return

        logs = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
            self.audit_logs = list(reversed(logs))[:50]
        except Exception as exc:
            pass

    @rx.event
    def stop_query(self) -> None:
        token = self.router.session.client_token
        task = _ACTIVE_TASKS.get(token)
        if task and not task.done():
            task.cancel()
            self.status_text = "Stopped"
            self.busy = False

    async def _run_intercept(self, query: str) -> None:
        import asyncio
        result = await asyncio.to_thread(QueryInterceptor().intercept, query)
        self.result_json = json.dumps(result, indent=2)
        self.status_text = str(result.get("status", "done")).capitalize()
        self.tool_name = str(result.get("tool_name", "-"))
        self.version_text = str(result.get("version", "-"))
        self.tool_path = str(result.get("tool_path", "-"))
        
        # Update history list stored in LocalStorage
        history_entry = f"{self.tool_name} {self.version_text} :: {query}"
        try:
            current_history = json.loads(self.history_json)
        except Exception:
            current_history = []
        if not isinstance(current_history, list):
            current_history = []
        new_history = [history_entry, *current_history][:10]
        self.history_json = json.dumps(new_history)

    @rx.event
    async def submit_query(self) -> Any:
        if self.busy:
            return
        query = self.query_text.strip()
        if not query:
            self.status_text = "Enter a query first."
            return

        self.busy = True
        self.status_text = "Publishing tool..."
        yield

        import asyncio
        loop = asyncio.get_running_loop()
        token = self.router.session.client_token
        task = loop.create_task(self._run_intercept(query))
        _ACTIVE_TASKS[token] = task

        try:
            await task
        except asyncio.CancelledError:
            self.status_text = "Stopped"
            self.result_json = json.dumps({"status": "cancelled", "message": "User stopped execution."}, indent=2)
        except Exception as exc:
            self.status_text = f"Error: {exc}"
            self.result_json = json.dumps({"error": str(exc)}, indent=2)
        finally:
            self.busy = False
            _ACTIVE_TASKS.pop(token, None)
            self._save_last_run()
            self.load_audit_logs()

    @rx.var
    def history(self) -> list[str]:
        try:
            return json.loads(self.history_json)
        except Exception:
            return []

    @rx.var
    def history_is_empty(self) -> bool:
        return len(self.history) == 0


def _info_card(icon_tag: str, label: str, value: Any) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(tag=icon_tag, size=18, color="#818cf8"),
            bg="rgba(129, 140, 248, 0.08)",
            padding="0.5rem",
            border_radius="10px",
            border="1px solid rgba(129, 140, 248, 0.15)",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.vstack(
            rx.text(
                label,
                font_size="0.75rem",
                color="#94a3b8",
                text_transform="uppercase",
                letter_spacing="0.05em",
                font_family="Space Grotesk",
                font_weight="bold",
            ),
            rx.text(
                value,
                font_family="Fira Code",
                font_size="0.85rem",
                color="#cbd5e1",
                word_break="break-all",
            ),
            align="start",
            spacing="1",
        ),
        align="center",
        spacing="3",
        padding="1rem",
        bg="rgba(15, 23, 42, 0.4)",
        border="1px solid rgba(255, 255, 255, 0.05)",
        border_radius="14px",
        backdrop_filter="blur(10px)",
        width="100%",
        transition="all 0.2s ease",
        _hover={"border_color": "rgba(129, 140, 248, 0.25)", "bg": "rgba(15, 23, 42, 0.5)"},
    )


def _audit_row(log: Any) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.cond(
                        log["status"] == "published",
                        rx.badge("Published", color_scheme="green", variant="surface"),
                        rx.badge("Rejected", color_scheme="red", variant="surface"),
                    ),
                    rx.text(
                        log["timestamp"],
                        font_size="0.75rem",
                        color="#64748b",
                        font_family="Fira Code",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.text(
                    log["query"],
                    font_size="0.9rem",
                    color="#cbd5e1",
                    font_family="Plus Jakarta Sans",
                    font_weight="500",
                ),
                align="start",
                spacing="1",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Intent:", font_size="0.75rem", color="#94a3b8", font_family="Space Grotesk"),
                    rx.badge(log["intent"], variant="outline", color_scheme="indigo"),
                    align="center",
                    spacing="1",
                ),
                rx.hstack(
                    rx.text("Tool:", font_size="0.75rem", color="#94a3b8", font_family="Space Grotesk"),
                    rx.text(
                        log["tool_name"],
                        " (",
                        log["version"],
                        ")",
                        font_size="0.8rem",
                        color="#818cf8",
                        font_family="Fira Code",
                    ),
                    align="center",
                    spacing="1",
                ),
                align="end",
                spacing="1",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        padding="1rem 1.25rem",
        bg="rgba(15, 23, 42, 0.35)",
        border="1px solid rgba(255, 255, 255, 0.05)",
        border_radius="12px",
        width="100%",
        _hover={"border_color": "rgba(129, 140, 248, 0.25)"},
        transition="border-color 0.15s ease",
    )


@rx.page(route="/", title="Dynamic MCP Skill Hub")
def portal_page() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header Section
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Dynamic MCP Skill Hub",
                        size="9",
                        font_family="Space Grotesk",
                        font_weight="800",
                        bg_gradient="linear(to r, #c084fc, #818cf8, #22d3ee)",
                        bg_clip="text",
                        letter_spacing="-0.03em",
                    ),
                    rx.text(
                        "Translate natural-language requests into versioned, validated, and sandboxed MCP tools instantly.",
                        font_family="Plus Jakarta Sans",
                        color="#94a3b8",
                        font_size="1.05rem",
                        font_weight="400",
                    ),
                    align="start",
                    spacing="2",
                ),
                rx.badge(
                    PortalState.status_text,
                    size="3",
                    variant="surface",
                    color_scheme="indigo",
                    border_radius="99px",
                    padding="0.35rem 1rem",
                    font_family="Space Grotesk",
                    font_weight="bold",
                ),
                justify="between",
                align="center",
                width="100%",
                padding_bottom="1.5rem",
                border_bottom="1px solid rgba(255, 255, 255, 0.05)",
            ),
            
            # Workspace & Telemetry Tabs
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon(tag="terminal", size=16),
                            rx.text("Skill Generator", font_family="Space Grotesk"),
                            spacing="2",
                            align="center",
                        ),
                        value="generator",
                    ),
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon(tag="activity", size=16),
                            rx.text("Telemetry & Session Logs", font_family="Space Grotesk"),
                            spacing="2",
                            align="center",
                        ),
                        value="telemetry",
                    ),
                    margin_bottom="1rem",
                ),
                rx.tabs.content(
                    rx.vstack(
                        # Two-column Main Workspace Grid
                        rx.grid(
                            # Left Column: Prompt Input
                            rx.vstack(
                                rx.hstack(
                                    rx.icon(tag="terminal", size=18, color="#a78bfa"),
                                    rx.text("Describe Your Custom MCP Tool", font_family="Space Grotesk", font_weight="600", color="#cbd5e1"),
                                    align="center",
                                    spacing="2",
                                ),
                                rx.text_area(
                                    value=PortalState.query_text,
                                    on_change=PortalState.update_query,
                                    min_height="180px",
                                    placeholder="Describe the tool you want to create (e.g., 'Build me a simple math tool' or 'Create a weather lookup tool')...",
                                    font_family="Plus Jakarta Sans",
                                    font_size="0.95rem",
                                    color="#f1f5f9",
                                    bg="rgba(10, 10, 15, 0.45)",
                                    border="1px solid rgba(255, 255, 255, 0.08)",
                                    border_radius="14px",
                                    padding="1rem",
                                    width="100%",
                                    disabled=PortalState.busy,
                                ),
                                rx.cond(
                                    PortalState.busy,
                                    rx.vstack(
                                        rx.box(
                                            rx.hstack(
                                                rx.spinner(size="3", color="violet"),
                                                rx.text(PortalState.status_text, font_family="Space Grotesk", font_weight="600", color="#a855f7"),
                                                align="center",
                                                justify="center",
                                                spacing="3",
                                            ),
                                            padding="0.75rem",
                                            bg="rgba(168, 85, 247, 0.08)",
                                            border="1px solid rgba(168, 85, 247, 0.25)",
                                            border_radius="12px",
                                            width="100%",
                                        ),
                                        rx.button(
                                            rx.hstack(
                                                rx.icon(tag="square", size=16),
                                                rx.text("Stop Execution", font_family="Space Grotesk", font_weight="700"),
                                                spacing="2",
                                                align="center",
                                            ),
                                            on_click=PortalState.stop_query,
                                            width="100%",
                                            size="3",
                                            color_scheme="red",
                                            variant="soft",
                                            _hover={"cursor": "pointer"},
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="cpu", size=18),
                                            rx.text("Generate & Register Skill", font_family="Space Grotesk", font_weight="700"),
                                            align="center",
                                            spacing="2",
                                        ),
                                        on_click=PortalState.submit_query,
                                        width="100%",
                                        size="3",
                                        bg="linear-gradient(135deg, #a855f7 0%, #6366f1 100%)",
                                        color="#ffffff",
                                        border_radius="12px",
                                        _hover={
                                            "transform": "translateY(-2px)",
                                            "box_shadow": "0 0 24px rgba(99, 102, 241, 0.4)",
                                            "cursor": "pointer"
                                        },
                                        transition="all 0.2s ease",
                                    ),
                                ),
                                width="100%",
                                spacing="4",
                                align="stretch",
                            ),
                            # Right Column: Live Manifest Status
                            rx.vstack(
                                rx.hstack(
                                    rx.icon(tag="database", size=18, color="#34d399"),
                                    rx.text("Workspace Tool Registry Status", font_family="Space Grotesk", font_weight="600", color="#cbd5e1"),
                                    align="center",
                                    spacing="2",
                                ),
                                _info_card("cpu", "Active Tool", PortalState.tool_name),
                                _info_card("git-branch", "Current Version", PortalState.version_text),
                                _info_card("folder", "Storage Registry Path", PortalState.tool_path),
                                width="100%",
                                spacing="3",
                                align="stretch",
                            ),
                            columns={"initial": "1", "md": "2"},
                            spacing="5",
                            width="100%",
                        ),

                        # Result JSON Terminal Block
                        rx.box(
                            # Terminal Header
                            rx.hstack(
                                rx.hstack(
                                    rx.box(width="10px", height="10px", bg="#ff5f56", border_radius="50%"),
                                    rx.box(width="10px", height="10px", bg="#ffbd2e", border_radius="50%"),
                                    rx.box(width="10px", height="10px", bg="#27c93f", border_radius="50%"),
                                    spacing="2",
                                ),
                                rx.text("output_manifest.json", color="#64748b", font_family="Fira Code", font_size="0.8rem"),
                                rx.box(width="30px"),
                                justify="between",
                                width="100%",
                                padding="0.75rem 1.25rem",
                                bg="rgba(15, 23, 42, 0.6)",
                                border_bottom="1px solid rgba(255, 255, 255, 0.06)",
                                border_top_left_radius="14px",
                                border_top_right_radius="14px",
                            ),
                            # Terminal Content
                            rx.box(
                                rx.cond(
                                    PortalState.result_json == "",
                                    rx.text("No query executed yet. System logs and results will be displayed here.", color="#475569", font_style="italic", font_family="Plus Jakarta Sans"),
                                    rx.text(
                                        PortalState.result_json,
                                        color="#34d399",
                                        white_space="pre-wrap",
                                        font_family="Fira Code",
                                        font_size="0.85rem",
                                        line_height="1.5",
                                    ),
                                ),
                                padding="1.25rem",
                                bg="rgba(10, 10, 15, 0.4)",
                                border_bottom_left_radius="14px",
                                border_bottom_right_radius="14px",
                                overflow_x="auto",
                                max_height="450px",
                            ),
                            border="1px solid rgba(255, 255, 255, 0.08)",
                            border_radius="14px",
                            bg="rgba(15, 23, 42, 0.25)",
                            backdrop_filter="blur(16px)",
                            width="100%",
                        ),

                        # Recent Runs Audit Registry
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="history", size=18, color="#a78bfa"),
                                rx.heading("Execution Registry & Audit Logs", size="4", font_family="Space Grotesk", color="#cbd5e1"),
                                spacing="2",
                                align="center",
                            ),
                            rx.cond(
                                PortalState.history_is_empty,
                                rx.text("No tools have been generated in this session yet.", color="#475569", font_style="italic", font_family="Plus Jakarta Sans", padding="0.5rem 0"),
                                rx.vstack(
                                    rx.foreach(
                                        PortalState.history,
                                        lambda item: rx.hstack(
                                            rx.icon(tag="check_check", size=14, color="#10b981"),
                                            rx.text(item, font_family="Fira Code", font_size="0.85rem", color="#94a3b8"),
                                            align="center",
                                            spacing="3",
                                            padding="0.6rem 0.8rem",
                                            bg="rgba(16, 185, 129, 0.03)",
                                            border="1px solid rgba(16, 185, 129, 0.08)",
                                            border_radius="8px",
                                            width="100%",
                                            transition="transform 0.15s ease",
                                            _hover={"transform": "translateX(4px)", "bg": "rgba(16, 185, 129, 0.05)"},
                                        ),
                                    ),
                                    align="stretch",
                                    spacing="2",
                                    width="100%",
                                ),
                            ),
                            padding="1.25rem",
                            border="1px solid rgba(255, 255, 255, 0.06)",
                            border_radius="14px",
                            bg="rgba(15, 23, 42, 0.25)",
                            backdrop_filter="blur(16px)",
                            width="100%",
                            align="stretch",
                            spacing="3",
                        ),
                        spacing="6",
                        align="stretch",
                    ),
                    value="generator",
                ),
                rx.tabs.content(
                    # Telemetry Logs View
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="activity", size=18, color="#a855f7"),
                            rx.heading("Telemetry & Active Session Audit Logs", size="4", font_family="Space Grotesk", color="#cbd5e1"),
                            rx.spacer(),
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="refresh_cw", size=14),
                                    rx.text("Refresh Logs", font_family="Space Grotesk"),
                                    spacing="1",
                                    align="center",
                                ),
                                on_click=PortalState.load_audit_logs,
                                size="2",
                                variant="surface",
                                color_scheme="violet",
                                _hover={"cursor": "pointer"},
                            ),
                            align="center",
                            width="100%",
                            padding_bottom="0.5rem",
                        ),
                        rx.cond(
                            PortalState.audit_logs.length() == 0,
                            rx.text("No audit records found. Run a generation query to populate session activity logs.", color="#475569", font_style="italic", font_family="Plus Jakarta Sans", padding="2rem", text_align="center"),
                            rx.vstack(
                                rx.foreach(
                                    PortalState.audit_logs,
                                    _audit_row,
                                ),
                                spacing="3",
                                align="stretch",
                                width="100%",
                            ),
                        ),
                        align="stretch",
                        spacing="4",
                        width="100%",
                        padding="1.5rem",
                        bg="rgba(15, 23, 42, 0.25)",
                        border="1px solid rgba(255, 255, 255, 0.06)",
                        border_radius="14px",
                        backdrop_filter="blur(16px)",
                    ),
                    value="telemetry",
                ),
                default_value="generator",
                width="100%",
            ),
            
            width="min(1200px, calc(100% - 2rem))",
            spacing="6",
            padding="2rem 0",
            margin="0 auto",
            align="stretch",
        ),
        min_height="100vh",
        bg="radial-gradient(circle at 50% -20%, #1e1b4b 0%, #09090b 70%, #030303 100%)",
        color="#f1f5f9",
        padding="1rem",
        on_mount=PortalState.load_audit_logs,
    )
