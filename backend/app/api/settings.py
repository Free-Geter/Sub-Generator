from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json
import os

from ..config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# settings.json 持久化路径
_settings_file = os.path.join(settings.data_dir, "settings.json")


class SettingsUpdate(BaseModel):
    video_source_dir: Optional[str] = None
    translation_engine: Optional[str] = None
    deepl_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    whisper_model: Optional[str] = None
    default_target_lang: Optional[str] = None
    translation_prompt: Optional[str] = None


def _load_settings() -> dict:
    """从 settings.json 加载已保存的配置"""
    if os.path.isfile(_settings_file):
        try:
            with open(_settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_settings(data: dict):
    """将配置写入 settings.json"""
    os.makedirs(os.path.dirname(_settings_file), exist_ok=True)
    with open(_settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _mask_key(value: str) -> str:
    """隐藏 API Key 的中间部分"""
    if not value or len(value) <= 8:
        return value
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


# 启动时从 settings.json 加载已保存配置，覆盖内存中的默认值
_saved = _load_settings()
for _key, _value in _saved.items():
    if hasattr(settings, _key) and _value is not None and _value != "":
        object.__setattr__(settings, _key, _value)


@router.get("")
async def get_settings():
    """获取当前配置（隐藏敏感信息）"""
    return {
        "video_source_dir": settings.video_source_dir,
        "translation_engine": settings.translation_engine,
        "deepl_api_key": _mask_key(settings.deepl_api_key),
        "openai_api_key": _mask_key(settings.openai_api_key),
        "openai_base_url": settings.openai_base_url,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "whisper_model": settings.whisper_model,
        "default_target_lang": settings.default_target_lang,
        "translation_prompt": settings.translation_prompt,
        "data_dir": settings.data_dir,
    }


@router.put("")
async def update_settings(settings_update: SettingsUpdate):
    """更新配置（运行时生效，同时持久化到 settings.json）"""
    update_data = settings_update.model_dump(exclude_none=True)

    # 更新内存中的 settings 对象
    for key, value in update_data.items():
        if hasattr(settings, key):
            object.__setattr__(settings, key, value)

    # 持久化到 settings.json（合并已有内容）
    saved = _load_settings()
    saved.update(update_data)
    _save_settings(saved)

    return {"message": "配置已更新", "updated_fields": list(update_data.keys())}
