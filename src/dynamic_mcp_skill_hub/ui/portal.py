from __future__ import annotations

import asyncio
import json

import reflex as rx

from dynamic_mcp_skill_hub.agent import AgentOrchestrator
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
)


class PortalState(rx.State):
    chat_input: str = ""
    status_text: str = "Ready"
    activity_log: list[str] = ["Waiting for a request."]
    last_mode: str = "-"
    tool_name: str = "-"
    version_text: str = "-"
    tool_path: str = "-"
    result_json: str = ""
    messages: list[dict[str, str]] = [
        {
            "role": "assistant",
            "content": "Ask me to answer a question, or ask me to build or update a tool.",
        }
    ]
    busy: bool = False

    @rx.event
    def update_input(self, value: str) -> None:
        self.chat_input = value

    @rx.event
    def send_message(self) -> None:
        message = self.chat_input.strip()
        if not message or self.busy:
            return

        conversation = [*self.messages, {"role": "user", "content": message}]
        self.messages = conversation
        self.chat_input = ""
        self.busy = True
        self.status_text = "Queued"
        self.activity_log = ["Request queued."]
        yield PortalState.process_message(message, conversation)
        yield rx.scroll_to("chat-bottom-anchor")

    @rx.event
    def handle_key_down(self, key: str) -> None:
        if key == "Enter" and not self.busy:
            yield PortalState.send_message()

    @rx.event(background=True)
    async def process_message(
        self,
        message: str,
        conversation: list[dict[str, str]],
    ) -> None:
        try:
            async with self:
                self.status_text = "Planning"
                self.activity_log = ["Planning the request."]
            await asyncio.sleep(0.5)

            async with self:
                self.status_text = "Working"
                self.activity_log = ["Running the agent pipeline."]

            result = await asyncio.to_thread(
                AgentOrchestrator().chat,
                message,
                conversation,
            )

            async with self:
                self.last_mode = result.mode
                self.activity_log = result.activity_log or ["Done."]

                if result.tool_result:
                    self.tool_name = str(result.tool_result.get("tool_name", "-"))
                    self.version_text = str(result.tool_result.get("version", "-"))
                    self.tool_path = str(result.tool_result.get("tool_path", "-"))
                    self.result_json = json.dumps(result.tool_result, indent=2)
                else:
                    self.tool_name = "-"
                    self.version_text = "-"
                    self.tool_path = "-"
                    self.result_json = json.dumps({"mode": result.mode}, indent=2)

                self.messages = [
                    *self.messages,
                    {"role": "assistant", "content": result.assistant_text},
                ]
                self.status_text = "Done"
            yield rx.scroll_to("chat-bottom-anchor")
        except Exception as exc:
            async with self:
                self.status_text = "Error"
                self.result_json = json.dumps({"error": str(exc)}, indent=2)
                self.activity_log = [
                    "The request failed before completion.",
                    str(exc),
                ]
                self.messages = [
                    *self.messages,
                    {"role": "assistant", "content": f"I hit an error: {exc}"},
                ]
            yield rx.scroll_to("chat-bottom-anchor")
        finally:
            async with self:
                self.busy = False


def _metric(label: str, value: rx.Var[str]) -> rx.Component:
    return rx.box(
        rx.text(label, font_size="0.7rem", letter_spacing="0.1em", color=THEME_MUTED),
        rx.text(value, font_size="0.98rem", font_weight="600", color=THEME_TEXT),
        padding="0.9rem 1rem",
        border_radius="18px",
        bg=THEME_CARD_BG,
        border=f"1px solid {THEME_BORDER}",
        width="100%",
    )


def _message_bubble(message) -> rx.Component:
    is_user = message["role"] == "user"
    return rx.box(
        rx.vstack(
            rx.text(
                message["role"],
                font_size="0.72rem",
                letter_spacing="0.12em",
                text_transform="uppercase",
                color=THEME_MUTED,
            ),
            rx.text(
                message["content"],
                white_space="pre-wrap",
                line_height="1.7",
                color=THEME_TEXT,
            ),
            spacing="2",
            align="start",
        ),
        width="100%",
        padding="0.95rem 1rem",
        border_radius="18px",
        bg=rx.cond(
            is_user,
            dynamic_color("rgba(14, 165, 233, 0.08)", "rgba(8, 47, 73, 0.55)"),
            THEME_CARD_BG,
        ),
        border=f"1px solid {THEME_BORDER}",
    )


@rx.page(route="/", title="Dynamic MCP Skill Hub")
def portal_page() -> rx.Component:
    return layout_wrapper(
        "Chat Portal",
        "/",
        rx.grid(
            # Left Column: Workspace metrics & live activity log
            rx.vstack(
                content_panel(
                    "Workspace",
                    "Live tool state",
                    _metric("Tool", PortalState.tool_name),
                    _metric("Version", PortalState.version_text),
                    _metric("Path", PortalState.tool_path),
                ),
                content_panel(
                    "Activity Log",
                    "Live execution stages",
                    rx.box(
                        rx.vstack(
                            rx.foreach(
                                PortalState.activity_log,
                                lambda item: rx.box(
                                    rx.text(
                                        item,
                                        white_space="pre-wrap",
                                        color=THEME_TEXT,
                                        font_size="0.86rem",
                                    ),
                                    padding="0.65rem 0.8rem",
                                    border_radius="14px",
                                    bg="rgba(148, 163, 184, 0.05)",
                                    border=f"1px solid {THEME_BORDER}",
                                    width="100%",
                                ),
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        max_height="22rem",
                        overflow_y="auto",
                    ),
                ),
                spacing="4",
                align="stretch",
                width="100%",
            ),
            # Center Column: Main chat thread
            content_panel(
                "Conversation",
                "Talk to the agent and let it decide whether to answer or build",
                rx.box(
                    rx.vstack(
                        rx.foreach(PortalState.messages, _message_bubble),
                        rx.box(id="chat-bottom-anchor"),
                        spacing="3",
                        width="100%",
                    ),
                    id="chat-scroll",
                    max_height="32rem",
                    overflow_y="auto",
                    padding_right="0.2rem",
                    scroll_behavior="smooth",
                ),
                rx.box(
                    rx.text_area(
                        value=PortalState.chat_input,
                        on_change=PortalState.update_input,
                        on_key_down=PortalState.handle_key_down,
                        placeholder="Ask a question or ask to build a tool — press Enter or click Send...",
                        min_height="100px",
                        border_radius="18px",
                        bg=THEME_INPUT_BG,
                        color=THEME_TEXT,
                        border=f"1px solid {THEME_BORDER}",
                        disabled=PortalState.busy,
                        resize="none",
                    ),
                    rx.hstack(
                        rx.text(
                            rx.cond(
                                PortalState.busy,
                                "Agent is working... please wait.",
                                "Press Enter or Send · Agent answers, builds, or upgrades tools.",
                            ),
                            color=rx.cond(PortalState.busy, "#0ea5e9", THEME_MUTED),
                            font_size="0.88rem",
                        ),
                        premium_button(
                            rx.cond(PortalState.busy, "Working...", "Send"),
                            rx.cond(PortalState.busy, "loader-2", "send"),
                            PortalState.send_message,
                            disabled=PortalState.busy,
                        ),
                        justify="between",
                        align="center",
                        width="100%",
                    ),
                    spacing="3",
                ),
            ),
            # Right Column: Tool build outputs / JSON logs
            content_panel(
                "Artifacts",
                "Published output and JSON status",
                rx.box(
                    rx.text(
                        PortalState.result_json,
                        white_space="pre-wrap",
                        font_family="monospace",
                        font_size="0.84rem",
                        color=dynamic_color("#0369a1", "#dbeafe"),
                    ),
                    padding="1rem",
                    border_radius="18px",
                    bg=dynamic_color("#ffffff", "#020617"),
                    border=f"1px solid {THEME_BORDER}",
                    max_height="42rem",
                    overflow_y="auto",
                ),
            ),
            template_columns="0.95fr 1.55fr 1fr",
            gap="1.2rem",
            width="100%",
        ),
    )
