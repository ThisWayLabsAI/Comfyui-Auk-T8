from __future__ import annotations

import math
import re

TTS_TASK_KEYS = frozenset({"instruct_tts", "zero_shot_tts"})
AUTO_DURATION_MODE = "自动估算（TTS 推荐）"
AUTO_TASK_DURATION_MODE = "自动适配（按任务规则）"
MANUAL_DURATION_MODE = "手动指定"

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_SECONDS_PER_UTF8_BYTE = {"en": 0.0656, "zh": 0.0803}
_SAMPLE_RATE = 24_000
_HOP_LENGTH = 256
_SHORT_TEXT_BYTE_THRESHOLD = 10
_SHORT_TEXT_SPEED = 0.3


def _estimate_f5_seconds(
    text: str,
    *,
    short_text_speed: float,
    short_text_minimum: float,
    max_seconds: float,
) -> float:
    value = str(text or "").strip()
    if not value:
        raise ValueError("自动估算时长需要填写目标文本")

    fallback = "zh" if _CJK_RE.search(value) else "en"
    languages = ["zh" if _CJK_RE.fullmatch(char) else ("en" if char.isascii() and char.isalpha() else None) for char in value]
    next_languages: list[str | None] = [None] * len(value)
    next_language = None
    for index in range(len(value) - 1, -1, -1):
        if languages[index] is not None:
            next_language = languages[index]
        next_languages[index] = next_language

    weight = 0.0
    previous_language = None
    for index, char in enumerate(value):
        language = languages[index]
        if language is None:
            language = previous_language or next_languages[index] or fallback
        else:
            previous_language = language
        weight += len(char.encode("utf-8")) * _SECONDS_PER_UTF8_BYTE[language]

    is_short_text = len(value.encode("utf-8")) < _SHORT_TEXT_BYTE_THRESHOLD
    speed = short_text_speed if is_short_text else 1.0
    frames = int(weight * _SAMPLE_RATE / _HOP_LENGTH / speed)
    seconds = frames * _HOP_LENGTH / _SAMPLE_RATE
    result = max(short_text_minimum if is_short_text else 0.6, math.ceil(seconds * 10.0 - 1e-9) / 10.0)
    if result > float(max_seconds):
        raise ValueError(f"目标文本预计需要 {result:.1f}s，超过 {max_seconds:.0f}s；请缩短文本或分段生成")
    return result


def estimate_tts_seconds(text: str, *, max_seconds: float = 30.0) -> float:
    """Mirror AuK PE's F5 instruction-TTS duration baseline."""
    return _estimate_f5_seconds(
        text,
        short_text_speed=_SHORT_TEXT_SPEED,
        short_text_minimum=0.6,
        max_seconds=max_seconds,
    )


def estimate_zero_shot_tts_seconds(text: str, *, max_seconds: float = 30.0) -> float:
    """Estimate clone duration without stretching an ultra-short target into long pauses.

    The native clone node intentionally does not ask for a reference transcript. In
    that case the PE's short-text slowdown can turn two Chinese characters plus
    punctuation into a 2.4-second slot. Keep the normal F5 estimate for all longer
    text, but use a 1-second floor and no short-text slowdown for under 10 bytes.
    """
    return _estimate_f5_seconds(
        text,
        short_text_speed=1.0,
        short_text_minimum=1.0,
        max_seconds=max_seconds,
    )
