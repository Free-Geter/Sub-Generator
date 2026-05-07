import asyncio
from typing import List, Optional, Callable
from dataclasses import dataclass

from app.services.ollama_client import OllamaClient


@dataclass
class TranslationSegment:
    """翻译段落"""
    start_time: float
    end_time: float
    source_text: str
    translated_text: str


# DeepL target_lang 映射
DEEPL_LANG_MAP = {
    "zh": "ZH",
    "en": "EN-US",
    "ja": "JA",
    "ko": "KO",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
}


class Translator:
    """统一翻译接口，支持 DeepL / OpenAI / Ollama 三引擎切换"""

    def __init__(self, engine: str, config: dict):
        """
        Args:
            engine: "deepl" | "openai" | "ollama"
            config: 引擎配置字典
        """
        self.engine = engine
        self.config = config

        if engine == "ollama":
            self._ollama_client = OllamaClient(
                base_url=config.get("ollama_base_url", "http://localhost:11434"),
                model=config.get("ollama_model", "qwen2.5:7b"),
            )

    async def translate_segments(
        self,
        segments: List[dict],
        target_lang: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> List[TranslationSegment]:
        """批量翻译所有段落，逐段翻译，支持进度回调，失败自动重试（最多3次）"""
        results: List[TranslationSegment] = []
        total = len(segments)

        for i, seg in enumerate(segments):
            source_text = seg["source_text"]
            translated_text = ""

            for attempt in range(3):
                try:
                    translated_text = await self._translate_single(source_text, target_lang)
                    break
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(1)

            results.append(TranslationSegment(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                source_text=source_text,
                translated_text=translated_text,
            ))

            if progress_callback:
                progress = (i + 1) / total * 100
                progress_callback(progress)

        return results

    async def _translate_single(self, text: str, target_lang: str) -> str:
        """翻译单段文本，根据引擎调用不同实现"""
        if self.engine == "deepl":
            return await self._translate_with_deepl(text, target_lang)
        elif self.engine == "openai":
            return await self._translate_with_openai(text, target_lang)
        elif self.engine == "ollama":
            return await self._translate_with_ollama(text, target_lang)
        else:
            raise ValueError(f"Unsupported translation engine: {self.engine}")

    async def _translate_with_deepl(self, text: str, target_lang: str) -> str:
        """DeepL 翻译"""
        import deepl

        api_key = self.config.get("deepl_api_key", "")
        mapped_lang = DEEPL_LANG_MAP.get(target_lang, target_lang.upper())

        translator = deepl.Translator(api_key)
        result = await asyncio.to_thread(
            translator.translate_text, text, target_lang=mapped_lang
        )
        return result.text

    async def _translate_with_openai(self, text: str, target_lang: str) -> str:
        """OpenAI 翻译"""
        from openai import AsyncOpenAI

        api_key = self.config.get("openai_api_key", "")
        base_url = self.config.get("openai_base_url") or None

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Translate to {target_lang}. Only output translation."},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content.strip()

    async def _translate_with_ollama(self, text: str, target_lang: str) -> str:
        """使用 OllamaClient 翻译"""
        return await self._ollama_client.translate(text, target_lang)
