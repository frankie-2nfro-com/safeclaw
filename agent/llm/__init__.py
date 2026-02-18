"""
LLM providers. Each subfolder (ollama, gemini, etc.) contains a provider-specific implementation.
"""
from llm.base_llm import BaseLLM, LLMResponseError


def get_llm(workspace, provider: str = None, model: str = None) -> BaseLLM:
    """Factory: return the appropriate LLM instance. Uses provider to select class (OllamaLLM, GeminiLLM, etc.)."""
    import os
    # Provider/model: passed args first, then env (for callers without config, e.g. action_executor)
    provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    model = model or os.getenv("LLM_MODEL", "llama3.1:8B")

    if provider == "ollama":
        from llm.ollama.llm import OllamaLLM
        return OllamaLLM(workspace=workspace, provider=provider, model=model)
    #if provider == "openai":
    #    from llm.openai.llm import OpenAILLM
    #    return OpenAILLM(workspace=workspace, provider=provider, model=model)
    #if provider == "gemini":
    #    from llm.gemini.llm import GeminiLLM
    #    return GeminiLLM(workspace=workspace, provider=provider, model=model)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use ollama, openai, or gemini.")
