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
    THEME_INPUT_BG,
    THEME_CARD_BG,
    dynamic_color,
    premium_button,
    custom_badge,
)


class ToolsState(rx.State):
    tools: list[dict[str, str]] = []
    selected_tool: str = ""
    latest_version: str = ""
    selected_tool_code: str = ""
    selected_tool_spec: str = ""
    run_input: str = "{}"
    run_result: str = ""
    run_busy: bool = False
    show_run_panel: bool = False

    @rx.event
    def load_all_tools(self) -> None:
        from dynamic_mcp_skill_hub.storage.registry import FilesystemToolRegistry
        import json
        registry = FilesystemToolRegistry()
        tool_names = registry.list_all_tools()
        
        loaded_tools = []
        for name in tool_names:
            manifest = registry.get_tool_manifest(name)
            description = ""
            current_ver = "v1"
            if manifest:
                description = manifest.get("description", "")
                current_ver = manifest.get("current_version", "v1")
            
            # Fallback: scan versions folder
            versions = registry.list_version_names(name)
            if versions:
                current_ver = versions[-1]
                if not description:
                    try:
                        spec_file = registry.version_dir(name, current_ver) / "spec.json"
                        if spec_file.exists():
                            spec_data = json.loads(spec_file.read_text(encoding="utf-8"))
                            description = spec_data.get("description", "")
                    except Exception:
                        pass
            
            loaded_tools.append({
                "name": name,
                "description": description or "Dynamic custom MCP tool.",
                "latest_version": current_ver,
            })
        self.tools = loaded_tools

    @rx.event
    def select_tool(self, tool_name: str) -> None:
        self.selected_tool = tool_name
        self.run_result = ""
        self.show_run_panel = True
        
        # Load details
        from dynamic_mcp_skill_hub.storage.registry import FilesystemToolRegistry
        registry = FilesystemToolRegistry()
        versions = registry.list_version_names(tool_name)
        if not versions:
            self.latest_version = "v1"
        else:
            self.latest_version = versions[-1]

        # Read Code
        tool_dir = registry.version_dir(tool_name, self.latest_version)
        code_file = tool_dir / "tool.py"
        if code_file.exists():
            self.selected_tool_code = code_file.read_text(encoding="utf-8")
        else:
            self.selected_tool_code = "# Source code not found."

        # Read Spec
        spec_file = tool_dir / "spec.json"
        if spec_file.exists():
            try:
                spec_data = json.loads(spec_file.read_text(encoding="utf-8"))
                self.selected_tool_spec = json.dumps(spec_data, indent=2)
                
                # Pre-fill input box with examples if present
                examples = spec_data.get("examples", [])
                if examples and isinstance(examples, list) and examples[0].get("input"):
                    self.run_input = json.dumps(examples[0]["input"], indent=2)
                else:
                    self.run_input = "{}"
            except Exception:
                self.selected_tool_spec = "{}"
                self.run_input = "{}"
        else:
            self.selected_tool_spec = "{}"
            self.run_input = "{}"

    @rx.event
    def update_input(self, value: str) -> None:
        self.run_input = value

    @rx.event(background=True)
    async def execute_selected_tool(self) -> None:
        async with self:
            self.run_busy = True
            self.run_result = ""
        
        try:
            inputs_dict = json.loads(self.run_input)
            
            # Execute
            from dynamic_mcp_skill_hub.execution.sandbox_runner import SandboxRunner
            runner = SandboxRunner()
            
            tool_run = await rx.to_thread(
                runner.run,
                self.selected_tool,
                self.latest_version,
                inputs_dict,
            )
            
            async with self:
                if tool_run.error:
                    self.run_result = json.dumps({"error": tool_run.error}, indent=2)
                else:
                    self.run_result = json.dumps(tool_run.output, indent=2)
        except Exception as exc:
            async with self:
                self.run_result = json.dumps({"error": f"Failed parsing inputs / run error: {exc}"}, indent=2)
        finally:
            async with self:
                self.run_busy = False


def tool_list_card(tool: dict[str, str]) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(tool["name"], font_weight="700", color=THEME_TEXT, font_size="1rem"),
                rx.spacer(),
                custom_badge(tool["latest_version"], "blue"),
                align="center",
                width="100%",
            ),
            rx.text(
                tool["description"],
                font_size="0.86rem",
                color=THEME_MUTED,
                line_height="1.5",
                max_height="3rem",
                overflow="hidden",
            ),
            rx.hstack(
                rx.spacer(),
                premium_button(
                    "Inspect & Run",
                    "play",
                    ToolsState.select_tool(tool["name"]),
                ),
                width="100%",
            ),
            spacing="3",
            align="stretch",
        ),
        padding="1rem",
        border_radius="18px",
        bg=THEME_CARD_BG,
        border=f"1px solid {THEME_BORDER}",
        transition="transform 0.15s ease",
        _hover={"transform": "translateY(-2px)", "border_color": "#0ea5e9"},
        width="100%",
    )


@rx.page(route="/tools", title="Tools Manager - Dynamic MCP Skill Hub", on_load=ToolsState.load_all_tools)
def tools_page() -> rx.Component:
    return layout_wrapper(
        "Tools Manager",
        "/tools",
        rx.grid(
            # Column 1: Built Tools List
            content_panel(
                "Skill Workspace",
                "Explore all custom filesystem-based MCP tools currently published",
                rx.cond(
                    ToolsState.tools.length() == 0,
                    rx.center(
                        rx.vstack(
                            rx.icon("wrench", size=48, color=THEME_MUTED),
                            rx.text("No skills built yet.", color=THEME_MUTED),
                            spacing="2",
                        ),
                        padding="4rem",
                    ),
                    rx.vstack(
                        rx.foreach(ToolsState.tools, tool_list_card),
                        spacing="3",
                        width="100%",
                    ),
                ),
            ),
            # Column 2: Run & Sandbox Playground
            rx.cond(
                ToolsState.show_run_panel,
                rx.vstack(
                    content_panel(
                        "Execution Sandbox",
                        f"Run and inspect '{ToolsState.selected_tool}' ({ToolsState.latest_version})",
                        rx.vstack(
                            rx.text("Input Arguments (JSON)", font_weight="600", font_size="0.88rem", color=THEME_TEXT),
                            rx.text_area(
                                value=ToolsState.run_input,
                                on_change=ToolsState.update_input,
                                placeholder="{}",
                                min_height="120px",
                                font_family="monospace",
                                font_size="0.86rem",
                                border_radius="12px",
                                bg=THEME_INPUT_BG,
                                border=f"1px solid {THEME_BORDER}",
                            ),
                            premium_button(
                                rx.cond(ToolsState.run_busy, "Running sandbox...", "Run Tool"),
                                "play",
                                ToolsState.execute_selected_tool,
                                width="100%",
                                disabled=ToolsState.run_busy,
                            ),
                            spacing="3",
                            align="stretch",
                        ),
                        rx.vstack(
                            rx.text("Run Output", font_weight="600", font_size="0.88rem", color=THEME_TEXT),
                            rx.box(
                                rx.text(
                                    rx.cond(ToolsState.run_result, ToolsState.run_result, "No execution output yet."),
                                    white_space="pre-wrap",
                                    font_family="monospace",
                                    font_size="0.84rem",
                                    color=rx.cond(ToolsState.run_result, dynamic_color("#0284c7", "#38bdf8"), THEME_MUTED),
                                ),
                                padding="1rem",
                                border_radius="14px",
                                bg="rgba(148, 163, 184, 0.05)",
                                border=f"1px solid {THEME_BORDER}",
                                width="100%",
                                max_height="200px",
                                overflow_y="auto",
                            ),
                            spacing="2",
                            align="stretch",
                        ),
                    ),
                    # Spec detail
                    content_panel(
                        "Tool Specification",
                        "Published specification manifest JSON",
                        rx.box(
                            rx.text(
                                ToolsState.selected_tool_spec,
                                white_space="pre-wrap",
                                font_family="monospace",
                                font_size="0.8rem",
                            ),
                            padding="0.8rem",
                            border_radius="14px",
                            bg="rgba(148, 163, 184, 0.05)",
                            border=f"1px solid {THEME_BORDER}",
                            max_height="220px",
                            overflow_y="auto",
                        ),
                    ),
                    spacing="4",
                    align="stretch",
                ),
                content_panel(
                    "Playground",
                    "Select a custom tool from the workspace list to view, test, and run it",
                    rx.center(
                        rx.vstack(
                            rx.icon("circle_play", size=48, color=THEME_MUTED),
                            rx.text("Inspect a skill to open sandbox.", color=THEME_MUTED),
                            spacing="2",
                        ),
                        padding="6rem 0",
                    ),
                ),
            ),
            # Column 3: Source Code Viewer
            rx.cond(
                ToolsState.show_run_panel,
                content_panel(
                    "Python Source Code",
                    "Dynamically loaded version implementation",
                    rx.box(
                        rx.text(
                            ToolsState.selected_tool_code,
                            white_space="pre-wrap",
                            font_family="monospace",
                            font_size="0.8rem",
                        ),
                        padding="1rem",
                        border_radius="18px",
                        bg="#090d16",
                        color="#dbeafe",
                        border=f"1px solid {THEME_BORDER}",
                        max_height="640px",
                        overflow_y="auto",
                    ),
                ),
                content_panel(
                    "Code Viewer",
                    "Inspect the compiled Python module",
                    rx.center(
                        rx.vstack(
                            rx.icon("code", size=48, color=THEME_MUTED),
                            rx.text("Source code will load here.", color=THEME_MUTED),
                            spacing="2",
                        ),
                        padding="6rem 0",
                    ),
                ),
            ),
            template_columns="1fr 1.2fr 1.3fr",
            gap="1.2rem",
            width="100%",
        ),
    )
