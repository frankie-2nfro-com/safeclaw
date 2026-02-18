# Ollama LLM Setup

## 1. Install Ollama

1. Download from [ollama.com](https://ollama.com)
2. Install and start the Ollama service
3. Pull a model: `ollama pull llama3.1:8B`

## 2. Configure

Set in `.env` (or use defaults):

```
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8B
```

## 3. Run

Ollama runs locally on your network. The agent connects to `ollama serve` (default: localhost:11434).

```bash
cd agent
python start_agent.py
```

## 4. Flow

```
User input  →  Prompt (SOUL, memory, history)  →  Ollama  →  Response + actions
```
