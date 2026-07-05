from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from dynamic_mcp_skill_hub.interceptor import QueryInterceptor
from dynamic_mcp_skill_hub.llm import ModelRequest, ModelRouter, extract_json_object

AgentMode = Literal["answer", "tool_build", "tool_update"]


@dataclass(frozen=True)
class AgentResult:
    mode: AgentMode
    assistant_text: str
    tool_result: dict[str, Any] | None = None
    activity_log: list[str] = field(default_factory=list)


class AgentOrchestrator:
    def __init__(
        self,
        model_router: ModelRouter | None = None,
        interceptor: QueryInterceptor | None = None,
    ) -> None:
        self.model_router = model_router or ModelRouter()
        self.interceptor = interceptor or QueryInterceptor()

    def chat(self, user_message: str, conversation: list[dict[str, str]]) -> AgentResult:
        logs = []
        
        if self._looks_like_time_query(user_message):
            logs.append("Query matches built-in time handler pattern.")
            return AgentResult(
                mode="answer",
                assistant_text=self._answer_time_query(user_message),
                activity_log=logs,
            )

        logs.append(f"Planning route for: '{user_message}'")
        plan = self._plan(user_message, conversation)
        logs.append(f"Plan determined: {plan['mode']} (Reason: {plan.get('reason', '-')})")
        
        if plan["mode"] in {"tool_build", "tool_update"}:
            tool_request = plan.get("tool_request") or user_message
            logs.append(f"Triggering tool hub interceptor for: '{tool_request}'")
            tool_result = self.interceptor.intercept(tool_request)
            
            if tool_result.get("status") != "published":
                logs.append("Tool creation failed validation or publication.")
                return AgentResult(
                    mode=plan["mode"],
                    assistant_text=(
                        "I tried to build the tool, but validation or publishing did not pass. "
                        "Please refine the request and try again."
                    ),
                    tool_result=tool_result,
                    activity_log=logs,
                )
                
            tool_name = tool_result.get("tool_name", "-")
            version = tool_result.get("version", "-")
            logs.append(f"Tool '{tool_name}' ({version}) successfully published.")
            
            # Extract inputs matching the tool's schema
            spec = self._get_tool_spec(tool_name, version)
            inputs_schema = spec.get("inputs", {})
            logs.append(f"Tool input schema: {list(inputs_schema.get('properties', {}).keys())}")
            
            logs.append("Extracting input arguments from query...")
            inputs = self._extract_tool_inputs(user_message, inputs_schema)
            logs.append(f"Extracted arguments: {json.dumps(inputs)}")
            
            # Execute tool in a self-correction loop
            from dynamic_mcp_skill_hub.execution.sandbox_runner import SandboxRunner
            runner = SandboxRunner()
            
            retries = 3
            tool_run = None
            for attempt in range(retries):
                logs.append(f"Executing tool '{tool_name}' (attempt {attempt + 1}/{retries})...")
                tool_run = runner.run(tool_name, version, inputs)
                
                is_empty_output = False
                if not tool_run.error and isinstance(tool_run.output, dict):
                    # Check if all value fields (other than metadata) are empty
                    meaningful_vals = [
                        v for k, v in tool_run.output.items()
                        if v and k not in {"location_name", "input", "tool_name", "description", "status"}
                    ]
                    if not meaningful_vals:
                        is_empty_output = True
                        tool_run.error = "Tool returned empty or blank values, indicating API resolution failed."
                
                if not tool_run.error and not is_empty_output:
                    logs.append("Tool execution completed successfully.")
                    break
                    
                logs.append(f"Execution failed: {tool_run.error.splitlines()[0]}")
                # Load code to fix it
                from dynamic_mcp_skill_hub.config import get_settings
                settings = get_settings()
                code_path = Path(settings.tool_registry_dir) / tool_name / "versions" / version / "tool.py"
                if code_path.exists():
                    current_code = code_path.read_text(encoding="utf-8")
                    logs.append("Submitting traceback to LLM for self-correction...")
                    corrected_code = self._self_correct_code(current_code, tool_run.error)
                    if corrected_code:
                        code_path.write_text(corrected_code, encoding="utf-8")
                        logs.append("Applied code fix. Retrying...")
                    else:
                        logs.append("LLM failed to correct the code.")
                else:
                    logs.append("Tool source file not found; skipping correction.")
                    break
                    
            if tool_run and tool_run.error:
                logs.append("Tool execution failed after self-correction retries.")
                logs.append("Attempting fallback web grounding...")
                try:
                    from dynamic_mcp_skill_hub.research.tavily import TavilyResearchAdapter
                    researcher = TavilyResearchAdapter()
                    search_results = researcher.search(user_message)
                    logs.append(f"Found {len(search_results)} search results.")
                    summary = "\n".join(f"- {r.title}: {r.summary}" for r in search_results)
                    assistant_text = self._direct_answer_with_context(user_message, summary, conversation)
                    return AgentResult(
                        mode=plan["mode"],
                        assistant_text=assistant_text,
                        tool_result=tool_result,
                        activity_log=logs,
                    )
                except Exception as e:
                    logs.append(f"Search fallback failed: {e}")
                    return AgentResult(
                        mode=plan["mode"],
                        assistant_text=f"I created the tool, but execution failed: {tool_run.error}",
                        tool_result=tool_result,
                        activity_log=logs,
                    )
            
            # Formulate final response using tool output
            logs.append("Formulating final answer using tool result...")
            assistant_text = self._formulate_final_answer(user_message, tool_run.output or {}, conversation)
            return AgentResult(
                mode=plan["mode"],
                assistant_text=assistant_text,
                tool_result=tool_result,
                activity_log=logs,
            )

        logs.append("Answering user query directly.")
        return AgentResult(
            mode="answer",
            assistant_text=self._direct_answer(user_message, conversation),
            activity_log=logs,
        )

    def _plan(self, user_message: str, conversation: list[dict[str, str]]) -> dict[str, Any]:
        context = self._conversation_text(conversation)
        prompt = (
            f"Conversation context:\n{context}\n\n"
            f"Latest user request:\n{user_message}\n\n"
            "Return ONLY JSON with keys: mode, assistant_reply, tool_request, reason.\n"
            'mode must be one of "answer", "tool_build", or "tool_update".\n'
            "If the request requires executing calculations, looking up live data (like weather, search queries, stocks), "
            "or doing API integrations, choose tool_build or tool_update. Otherwise, choose answer."
        )
        try:
            response = self.model_router.generate(
                ModelRequest(
                    system=(
                        "You are the control layer for Dynamic MCP Skill Hub. Decide whether to answer "
                        "directly or build/update an executable tool to resolve the query."
                    ),
                    prompt=prompt,
                    json_mode=True,
                )
            )
            candidate = extract_json_object(response.text)
            mode = str(candidate.get("mode", "answer")).strip().lower()
            if mode not in {"answer", "tool_build", "tool_update"}:
                mode = "answer"
            return {
                "mode": mode,
                "assistant_reply": str(candidate.get("assistant_reply", "")).strip(),
                "tool_request": str(candidate.get("tool_request", "")).strip(),
                "reason": str(candidate.get("reason", "")).strip(),
            }
        except Exception:
            heuristic_mode = self._heuristic_mode(user_message)
            return {
                "mode": heuristic_mode,
                "assistant_reply": "",
                "tool_request": user_message,
                "reason": "fallback_heuristic",
            }

    def _direct_answer(self, user_message: str, conversation: list[dict[str, str]]) -> str:
        context = self._conversation_text(conversation)
        response = self.model_router.generate(
            ModelRequest(
                system=(
                    "You are a helpful AI assistant inside Dynamic MCP Skill Hub. Answer the user "
                    "clearly and directly."
                ),
                prompt=f"Conversation context:\n{context}\n\nUser request:\n{user_message}",
                json_mode=False,
            )
        )
        text = response.text.strip()
        return text or "I could not generate a response right now."

    def _extract_tool_inputs(self, user_message: str, schema: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"User request: {user_message}\n\n"
            f"Tool inputs schema: {json.dumps(schema)}\n\n"
            "Extract the arguments to pass to the tool. Return ONLY a JSON object mapping input parameter names to values."
        )
        try:
            response = self.model_router.generate(
                ModelRequest(
                    system="You extract structured tool inputs from natural language. Output JSON only.",
                    prompt=prompt,
                    json_mode=True
                )
            )
            return extract_json_object(response.text)
        except Exception:
            return {}

    def _get_tool_spec(self, tool_name: str, version: str) -> dict[str, Any]:
        try:
            from dynamic_mcp_skill_hub.config import get_settings
            settings = get_settings()
            path = Path(settings.tool_registry_dir) / tool_name / "versions" / version / "spec.json"
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _self_correct_code(self, current_code: str, error_message: str) -> str:
        prompt = (
            f"The following Python code failed during runtime execution:\n"
            f"```python\n{current_code}\n```\n\n"
            f"Error details / Traceback:\n{error_message}\n\n"
            f"Note on common API issues:\n"
            f"- If you make requests to OpenStreetMap Nominatim ('nominatim.openstreetmap.org/search'), "
            f"  you MUST set a proper User-Agent header (e.g. {{'User-Agent': 'DynamicMCPSkillHub/1.0 (contact@example.com)'}}), "
            f"  otherwise it blocks with a 403 error. Always check if Nominatim returned search results "
            f"  before accessing indices.\n"
            f"- Alternatively, to lookup live weather, news, search queries, or stock data, you can use the Tavily Search API directly:\n"
            f"  URL: https://api.tavily.com/search\n"
            f"  Payload: {{\"api_key\": \"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\", \"query\": ...}}\n"
            f"  This is highly robust and avoids geocoding bugs.\n\n"
            f"Please identify the issue and rewrite the complete python code to fix it. Return ONLY the corrected executable Python code "
            f"containing the `run(input_data: dict[str, Any]) -> dict[str, Any]` function. Do not include markdown code block formatting."
        )
        try:
            response = self.model_router.generate_code(
                ModelRequest(
                    system="You are an expert Python debugger. Fix the code and output only corrected python code.",
                    prompt=prompt,
                    json_mode=False
                )
            )
            code = response.text.strip()
            if code.startswith("```"):
                parts = code.split("```")
                if len(parts) >= 3:
                    code = parts[1].strip()
                    if code.startswith("python"):
                        code = code[6:].strip()
            return code
        except Exception:
            return ""

    def _formulate_final_answer(self, user_message: str, tool_output: dict[str, Any], conversation: list[dict[str, str]]) -> str:
        context = self._conversation_text(conversation)
        prompt = (
            f"Conversation context:\n{context}\n\n"
            f"User request:\n{user_message}\n\n"
            f"Tool execution output:\n{json.dumps(tool_output, indent=2)}\n\n"
            f"Formulate a clear, direct, and human-friendly response to the user's request using the tool output."
        )
        try:
            response = self.model_router.generate(
                ModelRequest(
                    system="You are a helpful AI assistant. Answer the user clearly using the provided tool execution output.",
                    prompt=prompt,
                    json_mode=False
                )
            )
            return response.text.strip()
        except Exception:
            return f"Tool completed with output: {json.dumps(tool_output)}"

    def _direct_answer_with_context(self, user_message: str, search_context: str, conversation: list[dict[str, str]]) -> str:
        context = self._conversation_text(conversation)
        prompt = (
            f"Conversation context:\n{context}\n\n"
            f"Search groundings:\n{search_context}\n\n"
            f"User request:\n{user_message}\n\n"
            f"Answer the user's request clearly based on the provided search groundings."
        )
        try:
            response = self.model_router.generate(
                ModelRequest(
                    system="You are a helpful grounded AI assistant.",
                    prompt=prompt,
                    json_mode=False
                )
            )
            return response.text.strip()
        except Exception:
            return "I could not fetch search results to answer your query."

    @staticmethod
    def _conversation_text(conversation: list[dict[str, str]]) -> str:
        return "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in conversation[-10:]
        )

    @staticmethod
    def _heuristic_mode(user_message: str) -> AgentMode:
        lowered = user_message.lower()
        tool_keywords = [
            "build",
            "create",
            "tool",
            "workflow",
            "api",
            "lookup",
            "search",
            "weather",
            "version",
            "update",
            "publish",
            "mcp",
        ]
        if any(keyword in lowered for keyword in tool_keywords):
            return "tool_build"
        return "answer"

    @staticmethod
    def _looks_like_time_query(user_message: str) -> bool:
        lowered = user_message.lower()
        return any(
            keyword in lowered
            for keyword in [
                "current time",
                "local time",
                "time in",
                "what time",
                "clock in",
                "timezone",
            ]
        )

    @staticmethod
    def _answer_time_query(user_message: str) -> str:
        location = AgentOrchestrator._extract_location(user_message)
        tz, timezone_name = AgentOrchestrator._timezone_for_location(location)
        now = datetime.now(tz)
        offset = tz.utcoffset(now) or timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        abs_minutes = abs(total_minutes)
        timezone_offset = f"{sign}{abs_minutes // 60:02d}:{abs_minutes % 60:02d}"
        location_text = location or "the requested location"
        return (
            f"The current time in {location_text} is {now.strftime('%I:%M %p')} "
            f"on {now.strftime('%Y-%m-%d')} ({timezone_name}, UTC{timezone_offset})."
        )

    @staticmethod
    def _extract_location(user_message: str) -> str:
        lowered = user_message.lower()
        known_locations = [
            "dehradun",
            "uttarakhand",
            "india",
            "london",
            "tokyo",
            "new york",
            "usa",
            "united states",
            "united kingdom",
        ]
        for location in known_locations:
            if location in lowered:
                if location == "india":
                    return "India"
                if location == "usa":
                    return "USA"
                if location == "united states":
                    return "United States"
                if location == "united kingdom":
                    return "United Kingdom"
                return location.title()
        return ""

    @staticmethod
    def _timezone_for_location(location: str) -> tuple[timezone, str]:
        lowered = location.lower()
        if any(keyword in lowered for keyword in ["india", "dehradun", "uttarakhand"]):
            return timezone(timedelta(hours=5, minutes=30), name="IST"), "India Standard Time"
        if any(keyword in lowered for keyword in ["london", "united kingdom", "uk"]):
            return timezone.utc, "UTC"
        if any(keyword in lowered for keyword in ["new york", "united states", "usa"]):
            return timezone(timedelta(hours=-5), name="EST"), "Eastern Time"
        if "tokyo" in lowered or "japan" in lowered:
            return timezone(timedelta(hours=9), name="JST"), "Japan Standard Time"
        return timezone.utc, "UTC"
