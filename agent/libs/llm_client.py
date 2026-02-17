"""
LLM client. Supports multiple providers (ollama, openai, gemini).
Provider and model from env: LLM_PROVIDER, LLM_MODEL.
For openai/gemini: set API key in env.
"""
import os


def chat(prompt: str) -> str:
    """
    Send prompt to LLM, return response text.
    Uses LLM_PROVIDER and LLM_MODEL from env.
    """
    provider = (os.getenv("LLM_PROVIDER") or "ollama").lower()
    model = os.getenv("LLM_MODEL") or "llama3.1:8B"

    if provider == "ollama":
        return _chat_ollama(prompt, model)
    if provider == "openai":
        return _chat_openai(prompt, model)
    if provider == "gemini":
        return _chat_gemini(prompt, model)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use ollama, openai, or gemini.")


def _chat_ollama(prompt: str, model: str) -> str:
    import ollama
    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response.message.content


def _chat_openai(prompt: str, model: str) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set for provider=openai")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _chat_gemini(prompt: str, model: str) -> str:
    import google.generativeai as genai
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not set for provider=gemini")
    genai.configure(api_key=api_key)
    gemini = genai.GenerativeModel(model)
    response = gemini.generate_content(prompt)
    return response.text
