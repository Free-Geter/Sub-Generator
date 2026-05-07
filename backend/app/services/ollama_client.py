import httpx
from typing import Optional


class OllamaClient:
    """Ollama HTTP 客户端"""

    SYSTEM_PROMPT = """You are a professional translator. Translate the following text to {target_lang}.
Only output the translation, no explanations.
Preserve line breaks and formatting."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def translate(self, text: str, target_lang: str) -> str:
        """调用 Ollama API 进行翻译"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": text,
                    "system": self.SYSTEM_PROMPT.format(target_lang=target_lang),
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["response"].strip()

    async def check_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
