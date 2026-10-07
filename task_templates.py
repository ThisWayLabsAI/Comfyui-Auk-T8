from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskTemplate:
    key: str
    category: str
    label: str
    needs_audio: bool
    primary_label: str
    secondary_label: str
    duration_strategy: str = "manual"


@dataclass(frozen=True)
class TaskGuide:
    requirement: str
    example: str
    note: str


TASKS: tuple[TaskTemplate, ...] = (
    TaskTemplate("instruct_tts", "Speech generation", "Instruction TTS", False, "Target text", "Voice description", "tts"),
    TaskTemplate("zero_shot_tts", "Speech generation", "Voice cloning", True, "Target text", "Leave blank for voice cloning", "tts"),
    TaskTemplate("content_edit", "Audio editing", "Speech text editing", True,
                 "Edit request (one change at a time)", "Full source transcript (optional, duration estimate only)", "content"),
    TaskTemplate("lyric_edit", "Audio editing", "Lyric editing", True,
                 "Lyric replacement (one change at a time)", "Full source lyrics (optional, duration estimate only)", "content"),
    TaskTemplate("pitch", "Audio editing", "Pitch editing", True, "Semitone change", "Additional requirements (optional)", "source"),
    TaskTemplate("speed", "Audio editing", "Speed editing", True, "Speed multiplier", "Additional requirements (optional)", "speed"),
    TaskTemplate("volume", "Audio editing", "Volume editing", True, "Decibel change", "Additional requirements (optional)", "source"),
    TaskTemplate("emotion", "Audio editing", "Emotion editing", True, "Target emotion", "Additional requirements (optional)", "emotion"),
    TaskTemplate("timbre", "Audio editing", "Timbre editing", True, "Target voice description", "Additional requirements (optional)", "source"),
    TaskTemplate("deaccent", "Audio editing", "Accent removal", True, "Accent removal request", "Additional requirements (optional)", "source"),
    TaskTemplate("nonverbal", "Audio editing", "Nonverbal sound editing", True, "Add/remove request", "Leave blank", "nonverbal"),
    TaskTemplate("whisper", "Audio editing", "Whisper conversion", True, "Conversion direction", "Additional requirements (optional)", "source"),
    TaskTemplate("enhance", "Repair and separation", "Speech enhancement", True, "Cleanup request", "Additional requirements (optional)", "source"),
    TaskTemplate("quality", "Repair and separation", "Audio quality repair", True, "Audio defect or repair request", "Leave blank", "source"),
    TaskTemplate("speech_separate", "Repair and separation", "Speaker separation", True, "Speaker order", "Optional: denoise / dereverb", "source"),
    TaskTemplate("music_separate", "Repair and separation", "Music vocal extraction", True, "Vocals to keep", "Additional requirements (optional)", "source"),
    TaskTemplate("target_speaker", "Repair and separation", "Target speaker extraction", True, "Words spoken by the target", "Optional: denoise / dereverb", "source"),
)

# Stable aliases for upstream workflow files and programmatic clients.
LEGACY_TASK_LABELS = {
    "描述生成语音": "instruct_tts", "参考声音克隆": "zero_shot_tts",
    "语音文字编辑": "content_edit", "歌词编辑": "lyric_edit",
    "音高编辑": "pitch", "速度编辑": "speed", "音量编辑": "volume",
    "情绪编辑": "emotion", "音色编辑": "timbre", "去口音": "deaccent",
    "非语言声音编辑": "nonverbal", "耳语转换": "whisper", "语音增强": "enhance",
    "音质修复": "quality", "说话人分离": "speech_separate",
    "音乐人声提取": "music_separate", "指定说话人提取": "target_speaker",
}

TASK_BY_KEY = {task.key: task for task in TASKS}
TASK_BY_LABEL = {task.label: task for task in TASKS}
TASK_BY_LABEL.update({label: TASK_BY_KEY[key] for label, key in LEGACY_TASK_LABELS.items()})

TASK_GUIDES: dict[str, TaskGuide] = {
    "instruct_tts": TaskGuide(
        "No audio required. Enter the words to speak and a voice description.",
        "Target text: Welcome back. | Voice description: A warm, clear young female voice.",
        "Generates a voice from a description. Choose Voice cloning to match a recorded speaker.",
    ),
    "zero_shot_tts": TaskGuide(
        "Connect clear reference speech from one speaker. Enter only the new words to speak.",
        "Target text: Hello, and welcome to today's program.",
        "Leave the reference transcript and voice description blank; AuK uses its official fixed cloning prompt.",
    ),
    "content_edit": TaskGuide(
        "Connect ordinary spoken audio. Make one replacement, insertion, or deletion, using the exact original words.",
        "Replace 'this afternoon' with 'tomorrow morning'.",
        "Also: Insert 'everyone' after 'Hello'; Delete 'um'. The optional full transcript is used only for duration estimation.",
    ),
    "lyric_edit": TaskGuide(
        "Connect clean, isolated solo singing without accompaniment (a cappella). Replace one phrase matching the actual lyrics.",
        "Change 'hello tomorrow' to 'hello future' in the vocal recording.",
        "Use Speech text editing for spoken audio. The optional full lyrics are used only for duration estimation.",
    ),
    "pitch": TaskGuide(
        "Connect audio. Supported changes are +/-1, +/-2, or +/-3 semitones.",
        "+1 (one semitone higher) or -2 (two semitones lower)",
        "Zero and other values are outside the model's supported settings.",
    ),
    "speed": TaskGuide(
        "Connect audio. Supported multipliers: 0.5, 0.75, 1.25, 1.5, 2.0.",
        "0.75 (slower) or 1.25 (faster)",
        "1.0 makes no change. Duration is effective speech duration divided by the multiplier; manual duration and Float are ignored.",
    ),
    "volume": TaskGuide(
        "Connect audio. Supported changes are +/-5, +/-10, or +/-15 dB.",
        "+5 (louder) or -10 (quieter)",
        "Zero dB makes no change.",
    ),
    "emotion": TaskGuide(
        "Connect spoken audio. Choose happy, angry, sad, fearful, surprised, disgusted, calm, or excited.",
        "sad or fearful",
        "Preserves words and voice identity. Match the request language to the source speech; Chinese requests remain supported.",
    ),
    "timbre": TaskGuide(
        "Connect spoken audio and describe the desired voice.",
        "A deep, resonant young male voice",
        "Changes voice character while preserving the words. Choose a speech generation task to speak new text.",
    ),
    "deaccent": TaskGuide(
        "Connect spoken audio with a regional or dialect accent.",
        "Remove the regional accent",
        "Preserves the speaker's voice and words. The official prompt targets regional accent removal.",
    ),
    "nonverbal": TaskGuide(
        "Connect audio. Add or remove one event, such as laughter, breathing, a sigh, or a cough.",
        "Add laughter after 'welcome back'.",
        "Also: Remove all breathing; Add a sigh at the beginning. Unknown events or missing positions are rejected.",
    ),
    "whisper": TaskGuide(
        "Connect spoken audio. Specify whisper conversion or a return to normal speech.",
        "Convert to whisper",
        "Preserves the words and voice identity.",
    ),
    "enhance": TaskGuide(
        "Connect spoken audio to remove background noise and/or room reverberation.",
        "Remove noise and room reverb",
        "Keeps all speakers. Use Speaker separation to keep only one speaker.",
    ),
    "quality": TaskGuide(
        "Connect spoken audio to restore high frequencies/bandwidth or repair telephone, megaphone, or underwater coloration.",
        "Restore high frequencies and clarity; or: Remove the telephone effect",
        "Use Speech enhancement for ordinary background noise and room reverberation.",
    ),
    "speech_separate": TaskGuide(
        "Connect audio with multiple speakers. Select a speaker by the order in which they start speaking.",
        "The first speaker",
        "Keeps the selected speaker. Additional requirements may include denoise, dereverb, or both.",
    ),
    "music_separate": TaskGuide(
        "Connect mixed audio with accompaniment and specify the vocals to retain.",
        "Keep only singing vocals",
        "Use 'Keep all vocals' to retain both speech and singing while removing accompaniment.",
    ),
    "target_speaker": TaskGuide(
        "Connect audio with multiple speakers. Enter a short, exact phrase spoken by the target speaker.",
        "Welcome to today's program",
        "Uses those words to identify the speaker. Additional requirements may include denoise, dereverb, or both.",
    ),
}


def _clean_replacement_slot(value: str) -> str:
    # Users commonly write the quoted slot before the final sentence mark,
    # for example: Replace 'old' with 'new'.  Strip both classes together so
    # a quote revealed after removing the period cannot leak into the prompt.
    return value.strip().strip("\"'“”‘’ ，,。.!！")


def _quoted_slot(value: str) -> str:
    cleaned = _clean_replacement_slot(value)
    if not cleaned:
        raise ValueError("Edit content cannot be empty")
    return cleaned


def _canonical_replacement(value: str, *, lyrics: bool) -> str:
    text = str(value or "").strip()
    if lyrics:
        text = re.sub(r"^(?:把|将)?\s*(?:这段)?歌词(?:中(?:的)?)?\s*", "把", text, count=1)
    patterns = (
        (r"(?:把|将)?\s*(.+?)\s*(?:改成|改为|替换成|替换为|换成)\s*(.+)", "zh"),
        (r"(?:replace|change)\s+(.+?)\s+(?:with|to)\s+(.+?)(?:\s+in\s+the\s+(?:lyrics|vocal recording))?", "en"),
    )
    for pattern, language in patterns:
        match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
        if match is None:
            continue
        original = _clean_replacement_slot(match.group(1))
        replacement = _clean_replacement_slot(match.group(2))
        if not original or not replacement:
            break
        if original == replacement:
            raise ValueError("Original and replacement text are identical; no change would occur")
        if lyrics and language == "en":
            return f'Change "{original}" to "{replacement}" in the vocal recording.'
        if lyrics:
            return f"把这段歌词中的“{original}”改成“{replacement}”。"
        if language == "en":
            return f"Replace '{original}' with '{replacement}'."
        return f"把‘{original}’改成‘{replacement}’"
    task_name = "lyric editing" if lyrics else "speech text editing"
    raise ValueError(f"Invalid {task_name} request; follow the example and make one change at a time")


def _canonical_content_edit(value: str) -> str:
    text = str(value or "").strip()
    try:
        return _canonical_replacement(text, lyrics=False)
    except ValueError as replacement_error:
        if "Original and replacement text are identical" in str(replacement_error):
            raise

    # English requests produce the same canonical model instructions as upstream.
    english_insert = re.fullmatch(
        r"""(?:insert|add)\s+["'](.+?)["']\s+(before|after)\s+["'](.+?)["'][.!]?""",
        text, flags=re.IGNORECASE,
    )
    if english_insert:
        added, side, anchor = english_insert.groups()
        position = "前面" if side.casefold() == "before" else "后面"
        return f"在‘{_quoted_slot(anchor)}’{position}加上‘{_quoted_slot(added)}’"
    english_delete = re.fullmatch(
        r"""(?:delete|remove)\s+["'](.+?)["'](?:\s+(before|after)\s+["'](.+?)["'])?[.!]?""",
        text, flags=re.IGNORECASE,
    )
    if english_delete:
        target, side, anchor = english_delete.groups()
        if anchor:
            position = "前" if side.casefold() == "before" else "后"
            return f"删掉‘{_quoted_slot(anchor)}’{position}的‘{_quoted_slot(target)}’"
        return f"删掉‘{_quoted_slot(target)}’"

    quoted = r"[\"'“‘]?(.+?)[\"'”’]?"
    insert_match = re.fullmatch(
        rf"(?:在)?\s*{quoted}\s*(前面|前|后面|后)\s*(?:加上|加入|添加|插入)\s*{quoted}\s*[。.!！]?",
        text,
    )
    if insert_match is not None:
        anchor = _quoted_slot(insert_match.group(1))
        side = "前面" if insert_match.group(2).startswith("前") else "后面"
        added = _quoted_slot(insert_match.group(3))
        return f"在‘{anchor}’{side}加上‘{added}’"

    anchored_delete = re.fullmatch(
        rf"(?:删掉|删除|去掉)\s*{quoted}\s*(前面|前|后面|后)(?:的|那个)?\s*{quoted}\s*[。.!！]?",
        text,
    )
    if anchored_delete is not None:
        anchor = _quoted_slot(anchored_delete.group(1))
        side = "前" if anchored_delete.group(2).startswith("前") else "后"
        target = _quoted_slot(anchored_delete.group(3))
        return f"删掉‘{anchor}’{side}的‘{target}’"

    delete_match = re.fullmatch(r"(?:删掉|删除|去掉)\s*[\"'“‘]?(.+?)[\"'”’]?\s*[。.!！]?", text)
    if delete_match is not None:
        return f"删掉‘{_quoted_slot(delete_match.group(1))}’"

    raise ValueError("Invalid speech text edit; use the replacement, insertion, or deletion examples and make one change at a time")


def _signed_adjustment(value: str, *, allowed: tuple[int, ...], kind: str, unit: str) -> str:
    text = str(value or "").strip().replace("＋", "+").replace("－", "-")
    error_kind = {"音调": "pitch", "音量": "volume"}.get(kind, kind)
    error_unit = {"个半音": "semitones", "分贝": "dB"}.get(unit, unit)
    directions = {
        "increase": ("升高", "提高", "增加", "调高", "调大"),
        "decrease": ("降低", "减少", "调低", "调小"),
    }
    direction = None
    for candidate, words in directions.items():
        if any(word in text for word in words):
            if direction is not None and direction != candidate:
                raise ValueError(f"Conflicting {error_kind} directions: {value!r}")
            direction = candidate
    match = re.search(r"[+-]?\d+(?:\.0+)?", text)
    if match is None:
        choices = "/".join(str(item) for item in allowed)
        raise ValueError(f"Enter a signed {error_kind} value; supported values: +/-{choices} {error_unit}")
    remainder = (text[: match.start()] + text[match.end() :]).strip()
    for word in (*directions["increase"], *directions["decrease"], "个半音", "半音", "分贝", "dB", "db"):
        remainder = remainder.replace(word, "")
    if remainder.strip(" ，,。"):
        raise ValueError(f"Unrecognized {error_kind} value: {value!r}")
    numeric_text = match.group()
    numeric = float(numeric_text)
    if numeric == 0:
        raise ValueError(f"{error_kind} cannot be zero (no change)")
    sign_direction = "decrease" if numeric < 0 else "increase"
    if direction is not None and numeric_text.startswith(("+", "-")) and direction != sign_direction:
        raise ValueError(f"Conflicting {error_kind} direction and numeric sign: {value!r}")
    direction = direction or sign_direction
    magnitude = abs(numeric)
    if magnitude not in allowed:
        choices = "/".join(str(item) for item in allowed)
        raise ValueError(f"Supported {error_kind} values: {choices} {error_unit}; got {magnitude:g} {error_unit}")
    verb = "升高" if direction == "increase" else "降低"
    return f"将{kind}{verb}{magnitude:g}{unit}。"


def parse_speed_multiplier(value: str) -> float:
    text = str(value or "").strip().replace("×", "x")
    match = re.fullmatch(r"(0\.5|0\.75|1\.25|1\.5|2(?:\.0)?)(?:\s*(?:倍|[xX]))?", text)
    if match is None:
        raise ValueError("Speed multiplier must be 0.5, 0.75, 1.25, 1.5, or 2.0")
    return float(match.group(1))


def _speed_adjustment(value: str) -> str:
    multiplier = parse_speed_multiplier(value)
    formatted = "2.0" if multiplier == 2.0 else f"{multiplier:g}"
    return f"将语速调整为{formatted}倍。"


EMOTION_ALIASES = {
        "开心": "开心", "高兴": "开心", "愉快": "开心",
        "愤怒": "愤怒", "生气": "愤怒", "恼怒": "愤怒",
        "悲伤": "悲伤", "难过": "悲伤", "伤心": "悲伤",
        "恐惧": "恐惧", "害怕": "恐惧", "惊讶": "惊讶", "吃惊": "惊讶",
        "厌恶": "厌恶", "嫌弃": "厌恶", "反感": "厌恶",
        "平静": "平静", "冷静": "平静", "淡定": "平静",
        "兴奋": "兴奋", "激动": "兴奋",
        "happy": "开心", "angry": "愤怒", "sad": "悲伤", "fearful": "恐惧", "afraid": "恐惧",
        "surprised": "惊讶", "disgusted": "厌恶", "calm": "平静", "excited": "兴奋",
}

EMOTION_DURATION_MULTIPLIERS = {
    "悲伤": 1.22,
    "恐惧": 1.16,
    "开心": 1.06,
    "愤怒": 1.06,
    "惊讶": 1.06,
    "厌恶": 1.06,
    "平静": 1.06,
    "兴奋": 1.06,
}


def normalize_emotion(value: str) -> str:
    text = str(value or "").strip().strip("。.!！")
    for alias, label in EMOTION_ALIASES.items():
        if alias in text:
            return label
    raise ValueError("Supported emotions: happy, angry, sad, fearful, surprised, disgusted, calm, excited")


def emotion_duration_multiplier(value: str) -> float:
    return EMOTION_DURATION_MULTIPLIERS[normalize_emotion(value)]


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_EN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")


def spoken_duration_seconds(value: str | None) -> float:
    """Match AuK's prompt enhancer heuristic for spoken text duration."""
    text = str(value or "")
    duration = len(_CJK_RE.findall(text)) * 0.21 + len(_EN_WORD_RE.findall(text)) * 0.30
    if duration > 0:
        return duration
    return len(re.findall(r"\S", text)) * 0.21


def _content_duration_slots(task_key: str, primary: str) -> tuple[str | None, str | None]:
    instruction = build_instruction(task_key, primary)
    if task_key == "lyric_edit":
        match = re.fullmatch(r"把这段歌词中的“(.+?)”改成“(.+?)”。", instruction)
        if match is not None:
            return match.group(2), match.group(1)
        english_lyric = re.fullmatch(r'Change "(.+?)" to "(.+?)" in the vocal recording\.', instruction)
        if english_lyric is not None:
            return english_lyric.group(2), english_lyric.group(1)
        raise ValueError("Cannot parse lyric edit request")

    replace_match = re.fullmatch(r"把‘(.+?)’改成‘(.+?)’", instruction)
    if replace_match is not None:
        return replace_match.group(2), replace_match.group(1)
    english_replace = re.fullmatch(r"Replace '(.+?)' with '(.+?)'\.", instruction)
    if english_replace is not None:
        return english_replace.group(2), english_replace.group(1)
    insert_match = re.fullmatch(r"在‘.+?’(?:前面|后面)加上‘(.+?)’", instruction)
    if insert_match is not None:
        return insert_match.group(1), None
    delete_match = re.fullmatch(r"删掉(?:‘.+?’[前后]的)?‘(.+?)’", instruction)
    if delete_match is not None:
        return None, delete_match.group(1)
    raise ValueError("Cannot parse speech text edit request")


def content_scaled_seconds(task_key: str, primary: str, source_seconds: float, transcript: str = "") -> float:
    """Apply AuK's official content-edit duration heuristic without running ASR."""
    if task_key not in {"content_edit", "lyric_edit"}:
        raise ValueError(f"Unsupported content duration task: {task_key}")
    add_text, delete_text = _content_duration_slots(task_key, primary)
    transcript_duration = spoken_duration_seconds(transcript)
    if transcript_duration > 0:
        edited_duration = transcript_duration
        if add_text:
            edited_duration += spoken_duration_seconds(add_text)
        if delete_text:
            edited_duration -= spoken_duration_seconds(delete_text)
        return source_seconds * max(0.05, edited_duration) / transcript_duration
    if add_text and delete_text:
        original_duration = spoken_duration_seconds(delete_text)
        replacement_duration = spoken_duration_seconds(add_text)
        if original_duration > 0:
            return source_seconds * replacement_duration / original_duration
    return source_seconds


def nonverbal_duration_delta(primary: str) -> float:
    """Apply AuK's official event-family duration adjustment."""
    text = _nonverbal_instruction(primary).casefold()
    operation = "delete" if any(word in text for word in ("删除", "删掉", "去掉", "remove", "delete")) else "add"
    families = (
        (("呼吸", "换气", "喘", "breath", "breathing", "pant", "inhale", "exhale"), 0.35, -0.60),
        (("咂嘴", "咂舌", "啧", "吸鼻", "倒吸", "惊喘", "tsk", "smack", "sniff", "gasp"), 0.50, -1.00),
        (("笑", "叹气", "叹息", "咳", "清嗓", "语气", "laugh", "laughter", "chuckle", "sigh", "cough", "throat", "clearing"), 0.75, -1.05),
    )
    for keywords, add_delta, delete_delta in families:
        if any(keyword in text for keyword in keywords):
            return delete_delta if operation == "delete" else add_delta
    return -0.90 if operation == "delete" else 0.55


def _emotion_instruction(value: str) -> str:
    normalized = normalize_emotion(value)
    english = {
        "开心": "happy", "愤怒": "angry", "悲伤": "sad", "恐惧": "afraid",
        "惊讶": "surprised", "厌恶": "disgusted", "平静": "calm", "兴奋": "excited",
    }
    if re.search(r"[A-Za-z]", str(value or "")):
        return f"Say this in a {english[normalized]} tone"
    return f"将情感转变为{normalized}。"


def _whisper_instruction(value: str) -> str:
    text = str(value or "").strip()
    if any(word in text.casefold() for word in ("正常", "别耳语", "非耳语", "normal", "unwhisper")):
        return "把这段耳语转换成正常说话的声音。"
    if any(word in text.casefold() for word in ("耳语", "悄悄", "气声", "whisper")):
        return "用小声耳语的方式把这段话说出来。"
    raise ValueError("Enter 'Convert to whisper' or 'Convert to normal speech'")


def _enhance_instruction(value: str) -> str:
    text = str(value or "").strip().casefold()
    has_noise = any(word in text for word in ("噪", "杂音", "底噪", "noise", "denoise"))
    has_reverb = any(word in text for word in ("混响", "回声", "reverb", "echo"))
    if has_noise and not has_reverb:
        return "请只去除这段音频中的背景噪声，保留说话人原有的房间混响以及其它音色，输出等长的去噪结果。"
    if has_reverb and not has_noise:
        return "请只去除这段音频中的房间混响，保留原有的背景噪声以及其它音色，输出等长的去混响结果。"
    return "请对这段语音做纯净化处理，保留所有说话人的人声，并去除其中的噪声和混响，输出与输入等长的干净人声。"


def _music_separation_instruction(value: str) -> str:
    text = str(value or "").strip().casefold()
    if "所有人声" in text or "all vocals" in text:
        return "请保留所有人声，说话和歌唱都算，其余声音都去掉。"
    if any(word in text for word in ("歌声", "歌唱", "唱歌", "singing")):
        return "请只保留歌声，其余声音都去掉。"
    raise ValueError("Enter 'Keep only singing vocals' or 'Keep all vocals'")


_NONVERBAL_ALIASES = {
    "呼吸": "呼吸声", "换气": "换气声", "喘气": "喘气声", "breath": "breath",
    "大笑": "大笑声", "笑声": "笑声", "laugh": "laugh", "laughter": "laughter",
    "叹息": "叹息声", "叹气": "叹气声", "sigh": "sigh",
    "清嗓": "清嗓声", "throat clearing": "throat clearing", "咳嗽": "咳嗽声", "cough": "cough",
    "哦?": '"哦?"的疑问声', "嗯?": '"嗯?"的疑问声', "啊?": '"啊?"的疑问声', "诶?": '"诶?"的疑问声',
    "咦?": '"咦?"的疑问声', "哦": '"哦"的惊讶声', "嗯": '"嗯"的应答声', "呃": '"呃"的语气词',
    "啊": '"啊"的惊讶声',
    "咂舌": "咂舌声", "啧": "啧声", "吸鼻": "吸鼻声", "sniff": "sniff",
    "停顿": "停顿", "哇": '"哇"的惊讶声', "拉长": "拉长音", "拖音": "拖音",
    "诶": '"诶?"的疑问声', "哭": "哭声", "啜泣": "啜泣声", "crying": "crying", "sobbing": "sobbing",
    "哼": '"哼"的不满声', "倒吸": "倒吸气声", "惊喘": "惊喘声", "gasp": "gasp",
    "咂嘴": "咂嘴声", "哟": '"哟"的惊讶声', "咦": '"咦?"的疑问声',
    "偷笑": "偷笑声", "轻笑": "轻笑声", "哈欠": "哈欠声", "yawn": "yawn",
    "喷嚏": "喷嚏声", "sneeze": "sneeze", "嘘": "嘘声", "喘息": "喘息声",
    "拍手": "拍手声", "掌声": "掌声", "clap": "clap", "呻吟": "呻吟声", "moan": "moan",
    "吸气": "吸气声", "inhale": "inhale", "鼓掌": "鼓掌声", "applaud": "applaud",
    "哼唱": "哼唱声", "hum": "hum", "嘶": "嘶声", "hiss": "hiss", "呼气": "呼气声",
    "exhale": "exhale", "口哨": "口哨声", "whistle": "whistle", "打呼噜": "打呼噜声",
    "鼾": "鼾声", "snore": "snore", "grunt": "grunt",
}


def _nonverbal_sound(text: str) -> str:
    folded = text.casefold()
    for alias in sorted(_NONVERBAL_ALIASES, key=len, reverse=True):
        if alias.casefold() in folded:
            return _NONVERBAL_ALIASES[alias]
    raise ValueError("Unrecognized nonverbal sound; use laughter, sigh, breath, cough, throat clearing, sniff, yawn, or another supported event")


def _nonverbal_instruction(value: str) -> str:
    text = str(value or "").strip()
    sound = _nonverbal_sound(text)
    if any(word in text.casefold() for word in ("删除", "删掉", "去掉", "移除", "remove", "delete")):
        return f"删除音频中所有的{sound}。"
    if any(word in text.casefold() for word in ("开头", "开始", "最前", "beginning", "start")):
        return f"在语音开头增加{sound}。"
    if any(word in text.casefold() for word in ("结尾", "末尾", "最后", "at the end")):
        return f"在语音结尾增加{sound}。"
    english_anchor = re.search(r"""(before|after)\s+["'](.+?)["']""", text, flags=re.IGNORECASE)
    if english_anchor:
        side = "前" if english_anchor.group(1).casefold() == "before" else "后"
        return f"在“{_quoted_slot(english_anchor.group(2))}”{side}增加{sound}。"
    anchor_match = re.search(r"[‘'“\"](.+?)[’'”\"]\s*(前面|前|后面|后)", text)
    if anchor_match is None:
        raise ValueError("Specify removal, beginning/end, or a quoted anchor; for example: Add laughter after 'welcome back'")
    anchor = _quoted_slot(anchor_match.group(1))
    side = "前" if anchor_match.group(2).startswith("前") else "后"
    return f"在“{anchor}”{side}增加{sound}。"


def _cleanup_mode(value: str) -> str | None:
    text = str(value or "").casefold()
    denoise = any(word in text for word in ("去噪", "降噪", "去底噪", "去杂音", "去除噪声", "denoise", "remove noise", "remove background noise"))
    dereverb = any(word in text for word in ("去混响", "去除混响", "去回声", "去除回声", "dereverb", "remove reverb", "remove room reverb", "remove echo"))
    if denoise and dereverb:
        return "both"
    if denoise:
        return "denoise"
    if dereverb:
        return "dereverb"
    return None


def _quality_instruction(value: str) -> str:
    text = str(value or "").strip().casefold()
    cleanup = _cleanup_mode(text)
    if any(word in text for word in ("带宽", "高频", "超分辨率", "清晰度", "补频", "bandwidth", "high frequencies", "clarity", "super-resolution")):
        if cleanup == "both":
            return "请对这段语音做超分辨率/带宽扩展处理，恢复被削掉的高频成分，同时完成去噪与去混响，输出宽带纯净人声。"
        if cleanup == "denoise":
            return "请对这段语音做超分辨率/带宽扩展处理，恢复被削掉的高频成分，同时完成去噪，输出宽带纯净人声。"
        if cleanup == "dereverb":
            return "请对这段语音做超分辨率/带宽扩展处理，恢复被削掉的高频成分，同时去除房间混响，输出宽带纯净人声。"
        return "This audio suffers from limited bandwidth. Please restore it to a wideband, clear-sounding speech."
    effects = (
        ("telephone", ("电话", "手机", "窄带", "telephone", "narrowband")),
        ("megaphone", ("扩音器", "喇叭", "广播", "megaphone", "loudspeaker")),
        ("underwater", ("水下", "闷声", "发闷", "underwater", "muffled")),
        ("clipping", ("削波", "破音", "爆音", "clipping")),
        ("dropout", ("丢包", "瞬断", "断续", "dropout", "packet loss")),
        ("dc", ("直流", "偏置", "dc offset")),
    )
    prompts = {
        "telephone": {
            None: "This audio suffers from limited bandwidth. Please restore it to a wideband, clear-sounding speech.",
            "denoise": "请消除这段音频的电话带宽感，同时完成去噪，输出正常带宽的干净人声。",
            "dereverb": "请消除这段音频的电话带宽感，并去除房间混响，输出正常带宽的干净人声。",
            "both": "请消除这段音频的电话带宽感，并去除其中的噪声和混响，输出正常带宽的干净人声。",
        },
        "megaphone": {
            None: "请消除这段音频的扩音器音色，输出自然清晰的人声。",
            "denoise": "请消除这段音频的扩音器音色，同时完成去噪，输出自然清晰的人声。",
            "dereverb": "请消除这段音频的扩音器音色，并去除房间混响，输出自然清晰的人声。",
            "both": "请消除这段音频的扩音器音色，并去除其中的噪声和混响，输出自然清晰的人声。",
        },
        "underwater": {
            None: "请消除这段音频的水下闷声效果，输出清晰的宽带人声。",
            "denoise": "请消除这段音频的水下闷声效果，同时完成去噪，输出清晰的宽带人声。",
            "dereverb": "请消除这段音频的水下闷声效果，并去除房间混响，输出清晰的宽带人声。",
            "both": "请消除这段音频的水下闷声效果，并去除其中的噪声和混响，输出清晰的宽带人声。",
        },
        "clipping": {
            None: "请对这段音频做去破音处理，修复被硬削掉的波形，输出干净完整的人声。",
            "denoise": "请对这段音频做去破音处理，修复被硬削掉的波形，同时完成去噪，输出干净完整的人声。",
            "dereverb": "请对这段音频做去破音处理，修复被硬削掉的波形，并去除房间混响，输出干净完整的人声。",
            "both": "请对这段音频做去破音处理，修复被硬削掉的波形，并去除其中的噪声和混响，输出干净完整的人声。",
        },
        "dropout": {
            None: "请修复这段语音中的丢包脱落问题，输出连续自然的人声。",
            "denoise": "请修复这段语音中的丢包脱落问题，同时完成去噪，输出连续自然的人声。",
            "dereverb": "请修复这段语音中的丢包脱落问题，并去除房间混响，输出连续自然的人声。",
            "both": "请修复这段语音中的丢包脱落问题，并去除其中的噪声和混响，输出连续自然的人声。",
        },
        "dc": {
            None: "这段音频存在直流偏置，请把直流成分去掉，输出居中的干净人声。",
            "denoise": "这段音频存在直流偏置，请把直流成分去掉，同时完成去噪，输出居中的干净人声。",
            "dereverb": "这段音频存在直流偏置，请把直流成分去掉，并去除房间混响，输出居中的干净人声。",
            "both": "这段音频存在直流偏置，请把直流成分去掉，并去除其中的噪声和混响，输出居中的干净人声。",
        },
    }
    for effect, aliases in effects:
        if any(alias in text for alias in aliases):
            return prompts[effect][cleanup]
    raise ValueError("Specify 'Restore high frequencies and clarity' or an audio defect such as telephone, megaphone, or underwater coloration")


_ZH_ORDINALS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _speaker_order_instruction(primary: str, secondary: str) -> str:
    text = f"{primary} {secondary}".strip()
    match = re.search(r"第?\s*(\d+|[一二两三四五六七八九十])\s*(?:个|位)?(?:开始)?说话", text)
    if match is not None:
        raw = match.group(1)
        order = int(raw) if raw.isdigit() else _ZH_ORDINALS[raw]
    else:
        english = re.search(r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th)?)\s+speaker\b", text, flags=re.IGNORECASE)
        numbered = re.search(r"\bspeaker\s+(\d+)\b", text, flags=re.IGNORECASE)
        if english:
            raw = english.group(1).casefold()
            names = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth")
            order = names.index(raw) + 1 if raw in names else int(re.match(r"\d+", raw).group())
        elif numbered:
            order = int(numbered.group(1))
        else:
            raise ValueError("Speaker separation requires speaker order, for example 'the first speaker'")
    if order < 1:
        raise ValueError("Speaker order must start at 1")
    zh = next((key for key, number in _ZH_ORDINALS.items() if number == order and key != "两"), str(order))
    cleanup = _cleanup_mode(text)
    if cleanup == "denoise":
        return f"请保留第{zh}个开始说话的人，去掉其他说话人，并去除其中的背景噪声，输出单条纯净人声。"
    if cleanup == "dereverb":
        return f"请保留第{zh}个开始说话的人，去掉其他说话人，并去除房间混响，输出单条纯净人声。"
    if cleanup == "both":
        return f"请保留第{zh}个开始说话的人，去掉其他说话人，并去除其中的噪声和混响，输出单条纯净人声。"
    ordinals = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
    ordinal = ordinals.get(order, f"{order}th")
    return f"Keep only the {ordinal} speaker"


def _target_speaker_instruction(primary: str, secondary: str) -> str:
    spoken_text = _quoted_slot(primary)
    cleanup = _cleanup_mode(f"{primary} {secondary}")
    if cleanup == "denoise":
        return f"请在这段输入语音中保留说“{spoken_text}”的那位说话人，去掉其他说话人并对音频去噪，输出单条纯净人声。"
    if cleanup == "dereverb":
        return f"请在这段输入语音中保留说“{spoken_text}”的那位说话人，去掉其他说话人并去除房间混响，输出单条纯净人声。"
    if cleanup == "both":
        return f"请在这段输入语音中保留说“{spoken_text}”的那位说话人，去掉其他说话人，并去除其中的噪声和混响，输出单条纯净人声。"
    return f"Keep only the speaker who says “{spoken_text}”"


def _timbre_instruction(value: str) -> str:
    description = str(value or "").strip().strip("。")
    return f"请将这段音频的音色修改为符合以下描述的声音：“{description}”。"


def build_instruction(task_key: str, primary: str, secondary: str = "") -> str:
    primary = str(primary or "").strip()
    secondary = str(secondary or "").strip()
    if task_key not in TASK_BY_KEY:
        raise ValueError(f"Unknown task: {task_key}")
    if not primary:
        raise ValueError("Primary content cannot be empty")
    if task_key == "content_edit":
        return _canonical_content_edit(primary)
    if task_key == "lyric_edit":
        return _canonical_replacement(primary, lyrics=True)
    if task_key == "pitch":
        return _signed_adjustment(primary, allowed=(1, 2, 3), kind="音调", unit="个半音")
    if task_key == "speed":
        return _speed_adjustment(primary)
    if task_key == "volume":
        return _signed_adjustment(primary, allowed=(5, 10, 15), kind="音量", unit="分贝")
    if task_key == "emotion":
        return _emotion_instruction(primary)
    if task_key == "whisper":
        return _whisper_instruction(primary)
    if task_key == "enhance":
        return _enhance_instruction(primary)
    if task_key == "music_separate":
        return _music_separation_instruction(primary)
    if task_key == "quality":
        return _quality_instruction(primary)
    if task_key == "nonverbal":
        return _nonverbal_instruction(primary)
    if task_key == "speech_separate":
        return _speaker_order_instruction(primary, secondary)
    if task_key == "target_speaker":
        return _target_speaker_instruction(primary, secondary)
    if task_key == "timbre":
        return _timbre_instruction(primary)
    templates = {
        # The official field is required.  The local API supplies an explicit,
        # documented product default so programmatic callers remain compatible.
        "instruct_tts": f'请基于下面的描述: "{secondary or "自然、清晰的声音"}",生成语音内容"{primary}".',
        # Match AuK's training prompt exactly. Extra transcript or descriptive
        # prose can make the model continue the reference audio's content.
        "zero_shot_tts": f'Say the following with the same voice: "{primary}"',
        "deaccent": "请去掉这段语音里的方言口音，保持说话人音色一致。",
    }
    return templates[task_key].strip()
