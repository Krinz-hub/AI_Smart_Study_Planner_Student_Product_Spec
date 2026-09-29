import json
import re
from typing import Any, Dict, List, Optional
import httpx

from app.common.config import get_settings
from app.common.logging import get_logger

logger = get_logger("google_ai_provider")
settings = get_settings()

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def is_google_ai_available() -> bool:
    """Returns True if a Google API Key is configured."""
    return bool(settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY.strip())


async def is_ollama_available() -> bool:
    """Checks if local Ollama runtime is reachable."""
    base_url = settings.LLM_BASE_URL or "http://localhost:11434"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return res.status_code == 200
    except Exception:
        return False


async def generate_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
) -> Optional[str]:
    """Invokes Google Gemini 2.5 Flash via REST endpoint."""
    if not is_google_ai_available():
        return None

    model = settings.GOOGLE_AI_MODEL or "gemini-2.5-flash"
    url = f"{GEMINI_API_ENDPOINT}/{model}:generateContent?key={settings.GOOGLE_API_KEY}"

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        },
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            else:
                logger.warning("gemini_api_error", status_code=res.status_code, body=res.text[:200])
    except Exception as e:
        logger.warning("gemini_call_failed", error=str(e))

    return None


async def generate_ollama_fallback(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
) -> Optional[str]:
    """
    Invokes local Ollama instance (defaulting to lightweight model e.g. qwen2.5-coder:1.5b)
    as a fast, offline fallback when no Google API key is configured or when Gemini fails.
    """
    base_url = settings.LLM_BASE_URL or "http://localhost:11434"
    model = getattr(settings, "OLLAMA_LITE_MODEL", None) or getattr(settings, "LLM_MODEL", "qwen2.5-coder:1.5b")

    combined_prompt = f"System: {system_instruction}\n\nPrompt: {prompt}" if system_instruction else prompt

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": combined_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 512,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{base_url.rstrip('/')}/api/generate", json=payload)
            if res.status_code == 200:
                data = res.json()
                response_text = data.get("response", "").strip()
                if response_text:
                    logger.info("ollama_lite_fallback_success", model=model, chars=len(response_text))
                    return response_text
            else:
                logger.debug("ollama_api_error", status_code=res.status_code)
    except Exception as e:
        logger.debug("ollama_call_failed", error=str(e))

    return None


async def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
) -> Optional[str]:
    """
    Unified text generation interface:
    1. If GOOGLE_API_KEY is configured, queries Google Gemini 2.5 Flash.
    2. If Google API is unavailable or fails, automatically falls back to Ollama Lite model.
    3. Returns None if neither provider is reachable, allowing callers to use deterministic templates.
    """
    if is_google_ai_available():
        res = await generate_gemini(prompt, system_instruction, temperature)
        if res:
            return res
        logger.info("falling_back_to_ollama_after_gemini_failure")

    # Seamless fallback to Ollama Lite model
    ollama_res = await generate_ollama_fallback(prompt, system_instruction, temperature)
    if ollama_res:
        return ollama_res

    return None



def extract_json_from_llm_text(text: str) -> Optional[Dict[str, Any]]:
    """Extracts first valid JSON object from LLM response string."""
    try:
        # Direct parse
        return json.loads(text.strip())
    except Exception:
        pass

    # Extract markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Extract first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except Exception:
            pass

    return None
