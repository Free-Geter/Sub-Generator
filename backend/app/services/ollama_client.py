import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 目标语言的完整名称映射
LANG_NAME_MAP = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
}


class OllamaClient:
    """Ollama HTTP 客户端 — 专为字幕翻译优化"""

    # 日→中批量字幕翻译提示词
    SYSTEM_PROMPT_JA_ZH = (
        "你是一位专业的日文字幕翻译专家。请将以下日文字幕逐行翻译成自然流畅的中文。\n"
        "翻译要求：\n"
        "1. 输入格式为 [行号] 原文，请保持 [行号] 标记，只输出译文\n"
        "2. 严格保持行号顺序和数量一致，每行格式：[行号] 译文\n"
        "3. 不要合并、省略、拆分任何行\n"
        "4. 注意上下文连贯性，保持对话的流畅感\n"
        "5. 保持原文的语气和风格（口语/敬语/随意等）\n"
        "6. 人名、地名使用通用中文译名\n"
        "7. 遇到日文特有表达时，用地道的中文习惯说法替代"
    )

    # 通用批量翻译提示词
    SYSTEM_PROMPT_GENERAL = (
        "You are a professional translator. Translate the following lines to {target_lang}.\n"
        "Requirements:\n"
        "1. Input format is [N] original_text, keep [N] markers in output\n"
        "2. Output exactly one line per input line: [N] translated_text\n"
        "3. Do not merge, omit, or split any lines\n"
        "4. Maintain context across lines for natural flow\n"
        "5. Preserve the tone and style of the original\n"
        "6. Use natural, idiomatic expressions in the target language"
    )

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        timeout: int = 600,
        custom_system_prompt: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.custom_system_prompt = custom_system_prompt

    def _get_system_prompt(self, target_lang: str) -> str:
        """根据目标语言选择最优提示词，用户自定义优先"""
        if self.custom_system_prompt:
            # 用户自定义 prompt，支持 {target_lang} 占位符
            lang_name = LANG_NAME_MAP.get(target_lang, target_lang)
            return self.custom_system_prompt.format(target_lang=lang_name)
        if target_lang == "zh":
            # 中文目标 → 使用中文提示词，模型对中文指令响应更好
            return self.SYSTEM_PROMPT_JA_ZH
        lang_name = LANG_NAME_MAP.get(target_lang, target_lang)
        return self.SYSTEM_PROMPT_GENERAL.format(target_lang=lang_name)

    async def translate(self, text: str, target_lang: str) -> str:
        """调用 Ollama API 进行翻译"""
        system_prompt = self._get_system_prompt(target_lang)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": text,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 32768,      # 100 行中文译文约 5000-8000 tokens，留足余量
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data["response"].strip()
            logger.debug(f"Translated: {text[:50]}... → {result[:50]}...")
            return result

    async def check_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
