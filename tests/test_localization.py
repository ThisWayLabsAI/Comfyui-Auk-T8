from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from test_nodes import FakeEngine


def test_upstream_serialized_choices_remain_valid(plugin):
    schema = plugin.nodes.AuKGenerateEdit.define_schema()
    task_options = next(value.options for value in schema.inputs if value.id == "task")
    duration_options = next(value.options for value in schema.inputs if value.id == "duration_mode")
    for label, key in plugin.task_templates.LEGACY_TASK_LABELS.items():
        task = plugin.task_templates.TASK_BY_KEY[key]
        assert label in task_options
        assert task.label in task_options
        assert plugin.nodes.TASK_BY_LABEL[label] is plugin.nodes.TASK_BY_LABEL[task.label]
    for legacy, english in plugin.duration.DURATION_MODE_ALIASES.items():
        assert legacy in duration_options
        assert english in duration_options
        assert plugin.duration.normalize_duration_mode(legacy) == english


@pytest.mark.parametrize("task", ["描述生成语音", "Instruction TTS"])
@pytest.mark.parametrize("duration_mode", [
    "自动适配（按任务规则）", "Automatic adaptation (task rules)",
    "自动估算（TTS 推荐）", "Automatic estimate (TTS)",
    "手动指定", "Manual duration",
])
def test_legacy_and_english_requests_execute_identically(plugin, task, duration_mode):
    engine = FakeEngine()
    result = plugin.nodes.AuKGenerateEdit.execute(
        engine, task, "Hello, welcome back.", "A warm voice", 12.0, 42,
        duration_mode=duration_mode,
    )
    normalized_mode = plugin.duration.normalize_duration_mode(duration_mode)
    expected_seconds = 12.0 if normalized_mode == plugin.duration.MANUAL_DURATION_MODE else plugin.duration.estimate_tts_seconds("Hello, welcome back.")
    assert result[3] == expected_seconds
    expected = plugin.nodes.build_instruction("instruct_tts", "Hello, welcome back.", "A warm voice")
    assert result[1] == expected
    assert engine.call[0][0]["content"][0]["text"] == expected + "|<no_prompt_audio>|"
    assert json.loads(result[2])["duration_mode"] == normalized_mode


@pytest.mark.parametrize(("key", "english", "legacy"), [
    ("whisper", "Convert to whisper", "转换成耳语"),
    ("whisper", "Convert to normal speech", "转换成正常说话"),
    ("enhance", "Remove noise", "去噪"),
    ("enhance", "Remove room reverb", "去混响"),
    ("enhance", "Remove noise and room reverb", "去噪并去混响"),
    ("music_separate", "Keep only singing vocals", "只保留歌声"),
    ("music_separate", "Keep all vocals", "保留所有人声"),
    ("quality", "Restore high frequencies and clarity", "补充高频并提升清晰度"),
    ("quality", "Remove the telephone effect", "去掉电话感"),
    ("quality", "Remove the megaphone effect", "去掉扩音器音色"),
    ("speech_separate", "The first speaker", "第一个开始说话的人"),
    ("speech_separate", "Speaker 2", "第二个开始说话的人"),
    ("nonverbal", "Add a sigh at the beginning", "在开头增加sigh"),
    ("nonverbal", "Add laughter after 'welcome back'.", "在“welcome back”后增加laughter"),
    ("content_edit", "Insert 'everyone' after 'Hello'.", "在“Hello”后面加上“everyone”"),
    ("content_edit", "Delete 'um'.", "删掉“um”"),
    ("content_edit", "Delete 'um' before 'Hello'.", "删掉“Hello”前的“um”"),
])
def test_english_requests_preserve_canonical_model_instructions(plugin, key, english, legacy):
    assert plugin.nodes.build_instruction(key, english) == plugin.nodes.build_instruction(key, legacy)


def test_english_normal_speech_conversion_matches_preprocessing(plugin, monkeypatch):
    def unexpected_vad(*args):
        pytest.fail("Whisper-to-normal conversion must skip VAD")
    monkeypatch.setattr(plugin.preprocess, "_silero_speech_bounds", unexpected_vad)
    waveform = torch.full((1, 24000), 0.01)
    english_audio, english_metadata = plugin.preprocess.prepare_model_audio(
        waveform, 24000, "whisper", "Convert to normal speech",
    )
    legacy_audio, legacy_metadata = plugin.preprocess.prepare_model_audio(
        waveform, 24000, "whisper", "转换成正常说话",
    )
    assert torch.equal(english_audio, legacy_audio)
    assert english_metadata == legacy_metadata
    assert english_metadata["whisper_target_rms"] == plugin.preprocess.WHISPER_TO_NORMAL_TARGET_RMS


def test_generated_frontend_aliases_match_backend(plugin):
    root = Path(plugin.__file__).parent
    aliases = json.loads((root / "web/legacy_widget_values.json").read_text(encoding="utf-8"))
    assert aliases["task"] == {
        label: plugin.task_templates.TASK_BY_KEY[key].label
        for label, key in plugin.task_templates.LEGACY_TASK_LABELS.items()
    }
    assert aliases["duration_mode"] == plugin.duration.DURATION_MODE_ALIASES


def test_english_examples_have_no_untranslated_presentation(plugin):
    root = Path(plugin.__file__).parent / "example_workflows"
    for path in root.glob("*.json"):
        assert path.name.isascii()
        text = path.read_text(encoding="utf-8")
        assert not any("\u3400" <= char <= "\u9fff" or "\uac00" <= char <= "\ud7af" for char in text)
