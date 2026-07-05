from __future__ import annotations

from typing import Any

from dynamic_mcp_skill_hub.models import ToolSpec


def generate_schema(spec: ToolSpec) -> dict[str, Any]:
    return {
        "inputSchema": spec.inputs,
        "outputSchema": spec.outputs,
    }


def generate_test_cases(spec: ToolSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": scenario.name,
            "input": scenario.input,
            "expected": scenario.expected,
        }
        for scenario in spec.test_scenarios
    ]


def generate_python_tool_code(spec: ToolSpec, model_router: ModelRouter | None = None) -> str:
    tool_name = spec.name
    description = spec.description.replace("\"\"\"", "'")
    if _looks_like_time_lookup(spec):
        return _generate_time_tool_code(tool_name, description)

    if model_router is None:
        try:
            from dynamic_mcp_skill_hub.llm.model_router import ModelRouter
            model_router = ModelRouter()
        except Exception:
            pass

    if model_router is not None:
        try:
            from dynamic_mcp_skill_hub.llm.model_router import ModelRequest
            prompt = (
                f"You are writing a functional python tool for an MCP hub.\n"
                f"Tool Name: {spec.name}\n"
                f"Description: {spec.description}\n"
                f"Inputs Schema: {spec.inputs}\n"
                f"Outputs Schema: {spec.outputs}\n\n"
                f"Write the complete python code file containing a function with this signature:\n"
                f"```python\n"
                f"def run(input_data: dict[str, Any]) -> dict[str, Any]:\n"
                f"```\n"
                f"Requirements:\n"
                f"- Include all necessary imports at the top (e.g. from typing import Any, import httpx, urllib.request, json, os, datetime).\n"
                f"- Extract the inputs from `input_data` and perform the actual logic.\n"
                f"- Note: If you make requests to OpenStreetMap Nominatim ('nominatim.openstreetmap.org/search'), "
                f"  you MUST set a proper User-Agent header (e.g. {{'User-Agent': 'DynamicMCPSkillHub/1.0 (contact@example.com)'}}), "
                f"  otherwise it blocks with a 403 error. Always check if Nominatim returned search results "
                f"  before accessing indices.\n"
                f"- If the tool needs live information (like weather, news, search queries), you can use the Tavily search API via HTTP POST request:\n"
                f"  URL: https://api.tavily.com/search\n"
                f"  Payload: {{\"api_key\": os.getenv(\"TAVILY_API_KEY\", \"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\"), \"query\": <your search query>}}\n"
                f"  Extract details from the JSON response and return them matching the schema.\n"
                f"- Alternatively, you can use Open-Meteo or any other free public API to fetch current weather conditions.\n"
                f"- Return only the raw executable python code. Do not wrap it in markdown code blocks or python identifiers."
            )
            response = model_router.generate_code(
                ModelRequest(
                    system="You are an expert Python engineer. Output only clean, working, importable Python code without markdown blocks or explanation.",
                    prompt=prompt,
                    json_mode=False
                )
            )
            code = response.text.strip()
            # Clean markdown code blocks if the LLM wrapped it anyway
            if code.startswith("```"):
                parts = code.split("```")
                if len(parts) >= 3:
                    code = parts[1].strip()
                    if code.startswith("python"):
                        code = code[6:].strip()
            if "def run" in code:
                return code
        except Exception:
            pass

    return f'''"""Auto-generated tool: {tool_name}

{description}
"""

from __future__ import annotations
from typing import Any


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    return {{
        "tool_name": "{tool_name}",
        "description": "{description}",
        "input": input_data,
        "status": "ok",
    }}
'''


def _looks_like_time_lookup(spec: ToolSpec) -> bool:
    text = " ".join([spec.name, spec.description, *spec.tags]).lower()
    has_location_input = "location" in spec.inputs.get("properties", {})
    has_time_output = "current_time" in spec.outputs.get("properties", {})
    return has_location_input and has_time_output and any(
        keyword in text
        for keyword in [
            "time",
            "timezone",
            "current local time",
            "local time",
        ]
    )


def _generate_time_tool_code(tool_name: str, description: str) -> str:
    return f'''"""Auto-generated tool: {tool_name}

{description}
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _resolve_timezone(location: str) -> tuple[timezone, str]:
    text = location.lower()
    if any(keyword in text for keyword in ["india", "dehradun", "uttarakhand", "delhi", "mumbai", "kolkata"]):
        return timezone(timedelta(hours=5, minutes=30), name="IST"), "India Standard Time"
    if any(keyword in text for keyword in ["london", "uk", "united kingdom", "greenwich"]):
        return timezone.utc, "UTC"
    if any(keyword in text for keyword in ["new york", "usa", "united states", "est", "edt"]):
        return timezone(timedelta(hours=-5), name="EST"), "Eastern Time"
    if any(keyword in text for keyword in ["tokyo", "japan"]):
        return timezone(timedelta(hours=9), name="JST"), "Japan Standard Time"
    return timezone.utc, "UTC"


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    location = str(input_data.get("location", "")).strip()
    tz, timezone_name = _resolve_timezone(location)
    now = datetime.now(tz)
    offset = tz.utcoffset(now) or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    abs_minutes = abs(total_minutes)
    timezone_offset = f"{{sign}}{{abs_minutes // 60:02d}}:{{abs_minutes % 60:02d}}"
    return {{
        "tool_name": "{tool_name}",
        "description": "{description}",
        "location": location,
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone_name": timezone_name,
        "timezone_offset": timezone_offset,
        "status": "ok",
    }}
'''
