import asyncio
import logging
from typing import List, Optional, Callable
from dataclasses import dataclass

from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# 批量翻译配置：100 行/批，避免模型输出截断
BATCH_SIZE = 100


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
                custom_system_prompt=config.get("translation_prompt", ""),
            )

    async def translate_segments(
        self,
        segments: List[dict],
        target_lang: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> List[TranslationSegment]:
        """批量翻译所有段落，合并多行保留上下文"""
        results: List[TranslationSegment] = []
        total = len(segments)

        # 分批处理
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = segments[batch_start:batch_end]

            parsed = await self._translate_batch_with_retry(batch, batch_start, target_lang)

            for i, seg in enumerate(batch):
                results.append(TranslationSegment(
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    source_text=seg["source_text"],
                    translated_text=parsed[i] if i < len(parsed) else "",
                ))

            if progress_callback:
                progress = batch_end / total * 100
                progress_callback(progress)

        return results

    async def _translate_batch_with_retry(
        self, batch: List[dict], batch_start: int, target_lang: str
    ) -> List[str]:
        """翻译一个批次，若输出截断则拆分重试"""
        batch_end = batch_start + len(batch)
        total = batch_start + len(batch)  # not used for progress, just context

        parsed = await self._do_translate_batch(batch, batch_start, target_lang)
        non_empty = sum(1 for p in parsed if p)
        expected = len(batch)

        # 若翻译率 < 80%，自动拆分为 50/50 重试
        if non_empty < expected * 0.8 and expected > 50:
            logger.warning(
                f"Batch {batch_start // BATCH_SIZE + 1}: only {non_empty}/{expected} translated, "
                f"splitting into sub-batches for retry"
            )
            mid = expected // 2
            left = await self._do_translate_batch(batch[:mid], batch_start, target_lang)
            right = await self._do_translate_batch(batch[mid:], batch_start + mid, target_lang)
            parsed = left + right

        return parsed

    async def _do_translate_batch(
        self, batch: List[dict], batch_start: int, target_lang: str
    ) -> List[str]:
        """执行单次批量翻译并解析"""
        lines = []
        for i, seg in enumerate(batch):
            lines.append(f"[{batch_start + i + 1}] {seg['source_text']}")
        combined = "\n".join(lines)

        translated_text = ""
        for attempt in range(3):
            try:
                translated_text = await self._translate_batch(combined, target_lang)
                break
            except Exception as e:
                logger.warning(
                    f"Batch {batch_start // BATCH_SIZE + 1} translation attempt {attempt + 1}/3 failed: {e}"
                )
                if attempt < 2:
                    await asyncio.sleep(1)

        parsed = self._parse_batch_result(translated_text, len(batch))
        non_empty = sum(1 for p in parsed if p)
        logger.info(
            f"Batch {batch_start // BATCH_SIZE + 1}: "
            f"{batch_start + 1}-{batch_start + len(batch)}, "
            f"raw_output_len={len(translated_text)}, "
            f"parsed={len(parsed)}/{len(batch)} non_empty={non_empty}"
        )
        if non_empty < len(batch) * 0.8:
            logger.warning(
                f"Batch {batch_start // BATCH_SIZE + 1}: "
                f"only {non_empty}/{len(batch)} lines have translation, "
                f"raw_output_preview={translated_text[:200]!r}"
            )

        return parsed

    def _parse_batch_result(self, text: str, expected_count: int) -> List[str]:
        """解析批量翻译结果。

        策略：
        1. 优先按 [N] 标记切割（模型通常遵循此格式）
        2. 若解析出的行数不足，回退按行切割（模型可能省略了标记）
        3. 不足的行用空字符串补齐
        """
        import re

        if not text or not text.strip():
            logger.warning(f"_parse_batch_result: empty response, expected {expected_count} lines")
            return [""] * expected_count

        # ── 策略 1：按 [N] 标记切割 ──
        pattern = re.compile(r'\[(\d+)\]\s*')
        parts = pattern.split(text.strip())
        results: List[str] = []

        # parts 布局：[前缀, 数字1, 文本1, 数字2, 文本2, ...]
        i = 1  # 跳过第一个匹配前的前缀
        while i < len(parts):
            if i + 1 < len(parts):
                results.append(parts[i + 1].strip())
            i += 2

        marker_count = len(results)

        # ── 策略 2：标记不足时，回退按行切割 ──
        if marker_count < expected_count * 0.5:
            logger.warning(
                f"_parse_batch_result: only {marker_count}/{expected_count} lines parsed via [N] markers, "
                f"falling back to line-based split"
            )
            # 按换行切割，过滤空行和纯数字行
            lines = [l.strip() for l in text.strip().split('\n')]
            # 去掉只包含 [数字] 标记的行（模型有时会把标记单独放一行）
            marker_only = re.compile(r'^\[\d+\]$')
            fallback: List[str] = []
            for line in lines:
                if not line or marker_only.match(line):
                    continue
                # 去掉行首可能残留的 [N] 标记
                cleaned = pattern.sub('', line, count=1).strip()
                if cleaned:
                    fallback.append(cleaned)
            if len(fallback) > marker_count:
                results = fallback
                logger.info(f"_parse_batch_result: fallback yielded {len(results)} lines")

        # ── 补齐 ──
        shortfall = expected_count - len(results)
        if shortfall > 0:
            logger.warning(
                f"_parse_batch_result: missing {shortfall}/{expected_count} lines, padding with empty"
            )
            results.extend([""] * shortfall)
        elif shortfall < 0:
            logger.warning(
                f"_parse_batch_result: got {len(results)} lines but expected {expected_count}, truncating"
            )

        return results[:expected_count]

    async def _translate_batch(self, text: str, target_lang: str) -> str:
        """翻译批量文本"""
        if self.engine == "deepl":
            return await self._translate_with_deepl(text, target_lang)
        elif self.engine == "openai":
            return await self._translate_with_openai(text, target_lang)
        elif self.engine == "ollama":
            return await self._ollama_client.translate(text, target_lang)
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
