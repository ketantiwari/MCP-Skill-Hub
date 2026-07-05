from __future__ import annotations

import json
from typing import Any

import httpx

from dataclasses import dataclass
from typing import Literal

from dynamic_mcp_skill_hub.config import get_settings

ModelProvider = Literal["gemini", "groq", "nvidia_deepseek"]


@dataclass(frozen=True)
class ModelRequest:
    system: str
    prompt: str
    json_mode: bool = False


@dataclass(frozen=True)
class ModelResponse:
    provider: ModelProvider
    text: str


class ModelRouter:
    def generate(self, request: ModelRequest) -> ModelResponse:
        """General-purpose generation — tries Gemini first, falls back to Groq."""
        settings = get_settings()
        attempts = max(1, settings.model_max_retries)
        last_error: Exception | None = None

        for provider in ("gemini", "groq"):
            for _ in range(attempts):
                try:
                    return self._call_provider(provider, request)
                except Exception as exc:
                    last_error = exc

        raise RuntimeError(f"All model providers failed: {last_error}")

    def generate_code(self, request: ModelRequest) -> ModelResponse:
        """Specialized code generation — routes to DeepSeek V4 Pro first (superior coder),
        falls back to Gemini, then Groq."""
        settings = get_settings()
        attempts = max(1, settings.model_max_retries)
        last_error: Exception | None = None

        providers: list[ModelProvider] = []
        if settings.nvidia_api_key:
            providers.append("nvidia_deepseek")
        providers += ["gemini", "groq"]

        for provider in providers:
            for _ in range(attempts):
                try:
                    return self._call_provider(provider, request)
                except Exception as exc:
                    last_error = exc

        raise RuntimeError(f"All code-generation providers failed: {last_error}")

    def _call_provider(self, provider: ModelProvider, request: ModelRequest) -> ModelResponse:
        settings = get_settings()
        if provider == "gemini":
            return self._call_gemini(settings.google_model, settings.gemini_api_key, request)
        if provider == "nvidia_deepseek":
            return self._call_nvidia_deepseek(settings.nvidia_deepseek_model, settings.nvidia_api_key, request)
        return self._call_groq(settings.groq_model, settings.groq_api_key, request)

    def _call_gemini(self, model: str, api_key: str, request: ModelRequest) -> ModelResponse:
        if not api_key:
            raise RuntimeError("gemini API key is not configured")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": self._compose_prompt(request),
                        }
                    ],
                }
            ]
        }
        response = self._post_json(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            payload=payload,
        )
        candidates = response.get("candidates", [])
        text = ""
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                text = str(parts[0].get("text", ""))
        return ModelResponse(provider="gemini", text=text)

    def _call_groq(self, model: str, api_key: str, request: ModelRequest) -> ModelResponse:
        if not api_key:
            raise RuntimeError("groq API key is not configured")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": 0.2,
        }
        response = self._post_json(
            url="https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload=payload,
        )
        choices = response.get("choices", [])
        text = ""
        if choices:
            message = choices[0].get("message", {})
            text = str(message.get("content", ""))
        return ModelResponse(provider="groq", text=text)

    def _call_nvidia_deepseek(self, model: str, api_key: str, request: ModelRequest) -> ModelResponse:
        """Call DeepSeek V4 Pro via NVIDIA NIM (OpenAI-compatible endpoint)."""
        if not api_key:
            raise RuntimeError("NVIDIA API key is not configured")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 8192,
            "extra_body": {"chat_template_kwargs": {"thinking": False}},
        }
        response = self._post_json(
            url="https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload=payload,
        )
        choices = response.get("choices", [])
        text = ""
        if choices:
            message = choices[0].get("message", {})
            text = str(message.get("content", ""))
        return ModelResponse(provider="nvidia_deepseek", text=text)

    def _compose_prompt(self, request: ModelRequest) -> str:
        if request.json_mode:
            return (
                f"{request.system}\n\n"
                "Return only valid JSON.\n"
                f"{request.prompt}"
            )
        return f"{request.system}\n\n{request.prompt}"

    def _post_json(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        timeout = get_settings().model_timeout_ms / 1000
        response = httpx.post(
            url,
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned
    cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(cleaned)
    if not isinstance(obj, dict):
        raise ValueError("Model response did not contain a JSON object.")
    return obj
