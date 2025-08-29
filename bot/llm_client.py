# bot/llm_client.py
import os, requests

PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama | groq | together | fireworks | openai | ...
MODEL    = os.getenv("LLM_MODEL",  "llama-3.1-8b-instant")
TIMEOUT  = int(os.getenv("LLM_TIMEOUT", "120"))

def _post(url, json, headers=None):
    r = requests.post(url, json=json, headers=headers or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def generate(prompt: str, system: str | None = None) -> str:
    """
    Devuelve solo el texto final. No maneja memoria ni RAG: eso sigue en tu API.
    """
    if PROVIDER == "ollama":
        base = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
        payload = {"model": os.getenv("OLLAMA_MODEL", MODEL),
                   "prompt": prompt if not system else f"[SYSTEM]{system}\n{prompt}",
                   "stream": False}
        return _post(f"{base}", payload)["response"]

    # Proveedores con API estilo OpenAI (Groq/Together/Fireworks/OpenRouter)
    base = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    key  = os.getenv("LLM_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"}

    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
    }
    data = _post(f"{base}/chat/completions", payload, headers)
    return data["choices"][0]["message"]["content"]
