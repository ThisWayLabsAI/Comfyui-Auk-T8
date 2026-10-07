from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any

import folder_paths
import torch
import torchaudio
from comfy import model_management
from comfy.utils import ProgressBar
from comfy_api.v0_0_2 import ComfyExtension, io
from omegaconf import OmegaConf

from .duration import (
    AUTO_DURATION_MODE,
    DURATION_MODE_OPTIONS,
    normalize_duration_mode,
    AUTO_TASK_DURATION_MODE,
    MANUAL_DURATION_MODE,
    TTS_TASK_KEYS,
    estimate_tts_seconds,
    estimate_zero_shot_tts_seconds,
)
from .runtime import (
    MAX_SEQUENCE_SECONDS,
    QWEN_AUDIO_SAMPLE_RATE,
    AuKEngine,
    latent_frames_to_seconds,
    source_aligned_seconds,
    source_latent_frames,
    validate_sequence_duration,
)
from .preprocess import limit_vocal_output, prepare_model_audio, protect_audio_output
from .task_templates import (
    CONTROL_HELP,
    TASK_GUIDES as TASK_GUIDES,
    TASK_BY_LABEL,
    TASKS,
    build_instruction,
    content_scaled_seconds,
    emotion_duration_multiplier,
    nonverbal_duration_delta,
    parse_speed_multiplier,
)

logger = logging.getLogger("ComfyUI-AuK-T8")
AUK_ENGINE = io.Custom("AUK_ENGINE")
MODEL_ROOT = Path(folder_paths.models_dir) / "auk"
folder_paths.add_model_folder_path("auk", str(MODEL_ROOT), is_default=True)

MODEL_VARIANTS = {
    "AuK-Flash": ("AuK-Flash", "auk_flash.safetensors"),
    "AuK Base": ("AuK", "auk_base.safetensors"),
}


def load_manifest() -> dict[str, Any]:
    return json.loads(Path(__file__).with_name("MODEL_MANIFEST.json").read_text(encoding="utf-8"))


def model_search_roots() -> list[Path]:
    """Return ComfyUI's default and extra configured AuK model roots."""
    candidates = [MODEL_ROOT]
    try:
        candidates.extend(Path(path) for path in folder_paths.get_folder_paths("auk"))
    except KeyError:
        pass

    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate.expanduser().resolve()).casefold()
        if normalized not in seen:
            roots.append(candidate.expanduser().resolve())
            seen.add(normalized)
    return roots


def resolve_model_directory(directory_name: str, manifest: dict[str, Any]) -> Path:
    problems: list[str] = []
    for root in model_search_roots():
        directory = root / directory_name
        directory_problems: list[str] = []
        for filename, details in manifest[directory_name]["files"].items():
            path = directory / filename
            if not path.is_file():
                directory_problems.append(f"Missing {path}")
            elif path.stat().st_size != int(details["size"]):
                directory_problems.append(f"Size mismatch: {path}")
        if not directory_problems:
            return directory
        problems.extend(directory_problems)

    preview = "; ".join(problems[:5])
    if len(problems) > 5:
        preview += f"; {len(problems) - 5} more files"
    searched = ", ".join(str(root) for root in model_search_roots())
    raise FileNotFoundError(f"AuK model directory {directory_name} is incomplete: {preview}. Searched: {searched}")


def resolve_model_files(model_variant: str) -> tuple[Path, Path, Path]:
    if model_variant not in MODEL_VARIANTS:
        raise ValueError(f"Unknown model: {model_variant}")
    model_directory, checkpoint_name = MODEL_VARIANTS[model_variant]
    qwen_directory = "Qwen2.5-Omni-3B"
    manifest = load_manifest()["models"]
    try:
        model_path = resolve_model_directory(model_directory, manifest)
        qwen_path = resolve_model_directory(qwen_directory, manifest)
    except FileNotFoundError as exc:
        download_variant = "flash" if model_directory == "AuK-Flash" else "base"
        raise FileNotFoundError(
            f"{exc}. Place the folders from Hugging Face t8star/Auk-Comfy in ComfyUI/models/auk, "
            f"or run python download_models.py --variant {download_variant} in the node directory."
        ) from exc
    checkpoint = model_path / checkpoint_name
    config = model_path / "config.yaml"
    return checkpoint, config, qwen_path


def resolve_device(setting: str) -> torch.device:
    if setting == "auto":
        device = model_management.get_torch_device()
    else:
        device = torch.device(setting)
    if device.type not in {"cuda", "cpu"}:
        raise ValueError(f"AuK supports CUDA or CPU; ComfyUI selected {device}")
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise ValueError("CUDA was selected, but CUDA is unavailable in this PyTorch installation")
        index = torch.cuda.current_device() if device.index is None else device.index
        if index >= torch.cuda.device_count():
            raise ValueError(f"CUDA device does not exist: cuda:{index}")
        return torch.device("cuda", index)
    return torch.device("cpu")


def resolve_dtype(setting: str, device: torch.device) -> str:
    supports_bf16 = False
    if device.type == "cuda":
        with torch.cuda.device(device):
            supports_bf16 = torch.cuda.is_bf16_supported()
    if setting == "auto":
        if device.type == "cpu":
            return "fp32"
        return "bf16" if supports_bf16 else "fp16"
    if setting not in {"bf16", "fp16", "fp32"}:
        raise ValueError(f"Unsupported data type: {setting}")
    if device.type == "cpu" and setting != "fp32":
        raise ValueError("CPU inference requires fp32")
    if device.type == "cuda" and setting == "bf16" and not supports_bf16:
        raise ValueError("This CUDA device does not support bf16; select fp16")
    return setting


def normalize_audio(audio: dict[str, Any] | None) -> tuple[torch.Tensor, int] | None:
    if audio is None:
        return None
    if not isinstance(audio, dict) or "waveform" not in audio or "sample_rate" not in audio:
        raise ValueError("input_audio must be ComfyUI AUDIO")
    waveform = audio["waveform"]
    sample_rate = audio["sample_rate"]
    if not torch.is_tensor(waveform) or waveform.ndim != 3:
        shape = tuple(waveform.shape) if torch.is_tensor(waveform) else type(waveform).__name__
        raise ValueError(f"input_audio waveform must have shape [B, C, T]; got {shape}")
    if waveform.shape[0] != 1:
        raise ValueError(f"AuK accepts one audio clip at a time; got batch={waveform.shape[0]}")
    if waveform.shape[1] < 1 or waveform.shape[2] < 1:
        raise ValueError("Input audio is empty")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError(f"Invalid input sample rate: {sample_rate!r}")
    waveform = waveform[0].detach().to(device="cpu", dtype=torch.float32)
    if not torch.isfinite(waveform).all():
        raise ValueError("Input audio contains NaN or Inf")
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform.contiguous(), sample_rate


def resolve_generation_seconds(
    engine: AuKEngine,
    duration_strategy: str,
    audio: tuple[torch.Tensor, int] | None,
    requested_seconds: float,
    primary: str,
    task_key: str | None = None,
    duration_mode: str = MANUAL_DURATION_MODE,
    secondary: str = "",
    duration_base_seconds: float | None = None,
) -> float:
    """Resolve the output duration while preserving source length for fixed-length edits."""
    if duration_strategy == "source":
        if audio is None:
            raise ValueError("Source-aligned tasks require input audio")
        if duration_base_seconds is not None:
            target_frames = math.ceil(duration_base_seconds * engine.target_sample_rate / engine.downsample_rate)
            return latent_frames_to_seconds(engine, target_frames)
        return source_aligned_seconds(engine, audio)
    if duration_strategy == "speed":
        if audio is None:
            raise ValueError("Speed editing requires input audio")
        if duration_base_seconds is None:
            target_frames = math.ceil(source_latent_frames(engine, audio) / parse_speed_multiplier(primary))
        else:
            target_frames = math.ceil(
                duration_base_seconds * engine.target_sample_rate / engine.downsample_rate / parse_speed_multiplier(primary)
            )
        return latent_frames_to_seconds(engine, target_frames)
    if duration_strategy == "emotion":
        if audio is None:
            raise ValueError("Emotion editing requires input audio")
        if duration_base_seconds is None:
            target_frames = math.ceil(source_latent_frames(engine, audio) * emotion_duration_multiplier(primary))
        else:
            target_frames = math.ceil(
                duration_base_seconds
                * engine.target_sample_rate
                / engine.downsample_rate
                * emotion_duration_multiplier(primary)
            )
        return latent_frames_to_seconds(engine, target_frames)
    if duration_strategy == "content":
        if audio is None or task_key is None:
            raise ValueError("Speech text/lyric editing requires input audio")
        source_seconds = duration_base_seconds if duration_base_seconds is not None else source_aligned_seconds(engine, audio)
        target = content_scaled_seconds(task_key, primary, source_seconds, str(secondary or "").strip())
        target_frames = math.ceil(target * engine.target_sample_rate / engine.downsample_rate)
        return latent_frames_to_seconds(engine, target_frames)
    if duration_strategy == "nonverbal":
        if audio is None:
            raise ValueError("Nonverbal sound editing requires input audio")
        source_seconds = duration_base_seconds if duration_base_seconds is not None else source_aligned_seconds(engine, audio)
        target = max(0.1, source_seconds + nonverbal_duration_delta(primary))
        target_frames = math.ceil(target * engine.target_sample_rate / engine.downsample_rate)
        return latent_frames_to_seconds(engine, target_frames)
    duration_mode = normalize_duration_mode(duration_mode)
    if task_key in TTS_TASK_KEYS and duration_mode in {AUTO_DURATION_MODE, AUTO_TASK_DURATION_MODE}:
        if task_key == "zero_shot_tts":
            return estimate_zero_shot_tts_seconds(primary, max_seconds=MAX_SEQUENCE_SECONDS)
        return estimate_tts_seconds(primary, max_seconds=MAX_SEQUENCE_SECONDS)
    return float(requested_seconds)


class AuKModelLoader(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        devices = ["auto"] + [f"cuda:{index}" for index in range(torch.cuda.device_count())] + ["cpu"]
        return io.Schema(
            node_id="AuKModelLoader",
            display_name="AuK Model Loader",
            category="AuK · T8star-Aix",
            description="Loads AuK inside ComfyUI. ComfyUI manages staged model loading and GPU memory.",
            inputs=[
                io.Combo.Input("model_variant", display_name="Model", options=list(MODEL_VARIANTS), default="AuK Base"),
                io.Combo.Input("device", display_name="Device", options=devices, default="auto", advanced=True),
                io.Combo.Input(
                    "dtype",
                    display_name="Precision",
                    options=["auto", "bf16", "fp16", "fp32"],
                    default="auto",
                    advanced=True,
                ),
            ],
            outputs=[AUK_ENGINE.Output("engine", display_name="AuK Model")],
        )

    @classmethod
    def execute(cls, model_variant: str, device: str = "auto", dtype: str = "auto") -> io.NodeOutput:
        checkpoint, config, qwen = resolve_model_files(model_variant)
        model_config = OmegaConf.load(config)
        expected_name = MODEL_VARIANTS[model_variant][0]
        if str(model_config.model.get("name", "")) != expected_name:
            raise ValueError(f"Incorrect model type in configuration: {config}")
        resolved_device = resolve_device(device)
        resolved_dtype = resolve_dtype(dtype, resolved_device)
        logger.info("Loading %s on %s (%s)", model_variant, resolved_device, resolved_dtype)
        progress = ProgressBar(4)
        load_steps = {"config": 1, "qwen": 2, "vae": 3, "auk": 4}

        def load_progress(phase: str) -> None:
            model_management.throw_exception_if_processing_interrupted()
            progress.update_absolute(load_steps[phase])

        try:
            engine = AuKEngine(checkpoint, config, qwen, resolved_device, resolved_dtype, load_progress)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                f"Missing AuK dependency {exc.name!r}; use ComfyUI's Python to run pip install -r requirements.txt"
            ) from exc
        engine.model_variant = model_variant
        manifest = load_manifest()["models"]
        engine.model_revision = manifest[expected_name]["revision"]
        engine.qwen_revision = manifest["Qwen2.5-Omni-3B"]["revision"]
        return io.NodeOutput(engine)


class AuKGenerateEdit(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="AuKGenerateEdit",
            display_name="AuK Generate / Edit",
            category="AuK · T8star-Aix",
            description="Runs all official AuK tasks inside ComfyUI; editing duration is calculated using the official task rules.",
            inputs=[
                AUK_ENGINE.Input("engine", display_name="AuK Model"),
                io.Combo.Input("task", display_name="Task", options=list(TASK_BY_LABEL), default=TASKS[0].label),
                io.String.Input(
                    "primary",
                    display_name="1. Primary text (see task guide)",
                    tooltip="The selected task determines this box: target speech, one edit request, a numeric change, or a task instruction. See the task guide for the exact format.",
                    multiline=True,
                    default="",
                ),
                io.String.Input(
                    "secondary",
                    display_name="2. Secondary text (see task guide)",
                    tooltip="TTS: voice description. Speech/lyric editing: source transcript for duration only. Speaker separation: optional denoise/dereverb. Other tasks: unused; leave blank.",
                    multiline=True,
                    default="",
                ),
                io.Float.Input(
                    "generation_seconds",
                    display_name="Target duration (seconds; automatic for editing)",
                    default=3.0,
                    min=0.2,
                    max=MAX_SEQUENCE_SECONDS,
                    step=0.1,
                    display_mode=io.NumberDisplay.slider,
                ),
                io.Int.Input(
                    "seed",
                    default=42,
                    min=0,
                    max=0x7FFFFFFFFFFFFFFF,
                    control_after_generate=io.ControlAfterGenerate.randomize,
                    tooltip=CONTROL_HELP["seed"],
                ),
                io.Audio.Input("input_audio", display_name="Input / reference audio", optional=True),
                io.Int.Input("nfe_steps", display_name="NFE steps", default=32, min=4, max=64, advanced=True,
                             tooltip=CONTROL_HELP["nfe_steps"]),
                io.Float.Input(
                    "cfg_strength",
                    display_name="CFG strength",
                    tooltip=CONTROL_HELP["cfg_strength"],
                    default=2.0,
                    min=0.0,
                    max=5.0,
                    step=0.1,
                    advanced=True,
                ),
                io.Float.Input(
                    "sway_sampling_coef",
                    display_name="Sway coefficient",
                    tooltip=CONTROL_HELP["sway_sampling_coef"],
                    default=-1.0,
                    min=-1.0,
                    max=1.0,
                    step=0.1,
                    advanced=True,
                ),
                io.Combo.Input(
                    "duration_mode",
                    display_name="Duration adaptation mode",
                    options=DURATION_MODE_OPTIONS,
                    default=AUTO_TASK_DURATION_MODE,
                    tooltip="Automatic: estimates TTS duration from text; editing follows task rules and ignores target duration and connected Float. Manual duration applies only to TTS.",
                ),
            ],
            outputs=[
                io.Audio.Output("generated_audio", display_name="Generated audio"),
                io.String.Output("instruction", display_name="Final instruction"),
                io.String.Output("metadata", display_name="Run metadata JSON"),
                io.Float.Output("applied_seconds", display_name="Resolved target duration (seconds)"),
            ],
        )

    @classmethod
    def execute(
        cls,
        engine: AuKEngine,
        task: str,
        primary: str,
        secondary: str,
        generation_seconds: float,
        seed: int,
        input_audio: dict[str, Any] | None = None,
        nfe_steps: int = 32,
        cfg_strength: float = 2.0,
        sway_sampling_coef: float = -1.0,
        duration_mode: str = AUTO_TASK_DURATION_MODE,
    ) -> io.NodeOutput:
        if task not in TASK_BY_LABEL:
            raise ValueError(f"Unknown task: {task}")
        duration_mode = normalize_duration_mode(duration_mode)
        if duration_mode not in {AUTO_TASK_DURATION_MODE, AUTO_DURATION_MODE, MANUAL_DURATION_MODE}:
            raise ValueError(f"Unknown duration mode: {duration_mode}")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 0x7FFFFFFFFFFFFFFF:
            raise ValueError("Seed must be an integer from 0 to 9223372036854775807")
        if isinstance(nfe_steps, bool) or not isinstance(nfe_steps, int) or not 4 <= nfe_steps <= 64:
            raise ValueError("NFE steps must be an integer from 4 to 64")
        if not math.isfinite(float(cfg_strength)) or not 0 <= float(cfg_strength) <= 5:
            raise ValueError("CFG strength must be a finite number from 0 to 5")
        if not math.isfinite(float(sway_sampling_coef)) or not -1 <= float(sway_sampling_coef) <= 1:
            raise ValueError("Sway coefficient must be a finite number from -1 to 1")
        template = TASK_BY_LABEL[task]
        audio = normalize_audio(None if not template.needs_audio else input_audio)
        if template.needs_audio and audio is None:
            raise ValueError(f"{task} requires connected input or reference audio")
        preprocessing = None
        duration_base_seconds = None
        original_input_seconds = 0.0
        if audio is not None:
            waveform, sample_rate = audio
            original_input_seconds = waveform.shape[-1] / sample_rate
            validate_sequence_duration(engine, audio, 0.2)
            waveform, preprocessing = prepare_model_audio(waveform, sample_rate, template.key, primary)
            duration_base_seconds = float(preprocessing["speech_seconds_unpadded"])
            audio = (waveform, sample_rate)
        instruction = build_instruction(template.key, primary, secondary)
        requested_seconds = float(generation_seconds)
        target_seconds = resolve_generation_seconds(
            engine,
            template.duration_strategy,
            audio,
            requested_seconds,
            primary,
            template.key,
            duration_mode,
            secondary,
            duration_base_seconds,
        )
        validate_sequence_duration(engine, audio, target_seconds, input_seconds=original_input_seconds)
        if engine.is_flash:
            nfe_steps, cfg_strength, sway_sampling_coef = 4, 0.0, -1.0

        model_instruction = instruction if audio is not None else instruction + "|<no_prompt_audio>|"
        content: list[dict[str, Any]] = [{"type": "text", "text": model_instruction}]
        if audio is not None:
            waveform, sample_rate = audio
            qwen_waveform = waveform
            if sample_rate != QWEN_AUDIO_SAMPLE_RATE:
                qwen_waveform = torchaudio.functional.resample(waveform, sample_rate, QWEN_AUDIO_SAMPLE_RATE)
            content.append({"type": "audio", "audio": qwen_waveform.squeeze(0).contiguous().numpy()})
        messages = [{"role": "user", "content": content}]

        progress = ProgressBar(100)
        progress.update_absolute(1)
        current_phase = "preparing"
        sampling_updates = 0
        phase_progress = {
            "encoding_reference": 12,
            "encoding_instruction": 28,
            "sampling": 42,
            "decoding": 92,
        }

        def phase_callback(phase: str) -> None:
            nonlocal current_phase
            current_phase = phase
            progress.update_absolute(phase_progress.get(phase, progress.current))

        def interrupt_callback() -> None:
            nonlocal sampling_updates
            model_management.throw_exception_if_processing_interrupted()
            if current_phase == "sampling":
                sampling_updates += 1
                sampling_total = max(1, int(nfe_steps))
                progress.update_absolute(min(90, 42 + math.ceil(48 * sampling_updates / sampling_total)))

        started = time.perf_counter()
        waveform, sample_rate = engine.generate(
            messages,
            audio,
            target_seconds,
            int(nfe_steps),
            float(cfg_strength),
            float(sway_sampling_coef),
            int(seed),
            interrupt_callback,
            phase_callback,
        )
        waveform, vocal_peak_limited = limit_vocal_output(waveform, template.key, int(sample_rate))
        waveform, output_peak_protection = protect_audio_output(waveform)
        progress.update_absolute(100)
        effective_duration_strategy = (
            "auto_text" if template.key in TTS_TASK_KEYS and duration_mode in {AUTO_DURATION_MODE, AUTO_TASK_DURATION_MODE}
            else template.duration_strategy
        )
        metadata = {
            "model": engine.model_variant,
            "device": str(engine.device),
            "dtype": engine.dtype,
            "task": template.key,
            "seed": int(seed),
            "generation_seconds": target_seconds,
            "requested_generation_seconds": requested_seconds if math.isfinite(requested_seconds) else None,
            "duration_strategy": effective_duration_strategy,
            "duration_mode": duration_mode,
            "original_input_seconds": original_input_seconds,
            "prepared_input_seconds": 0.0 if audio is None else audio[0].shape[-1] / audio[1],
            "input_preprocessing": preprocessing,
            "vocal_output_peak_limited": vocal_peak_limited,
            "output_peak_protection": output_peak_protection,
            "sample_rate": int(sample_rate),
            "actual_output_seconds": waveform.shape[-1] / int(sample_rate),
            "nfe_steps": int(nfe_steps),
            "cfg_strength": float(cfg_strength),
            "sway_sampling_coef": float(sway_sampling_coef),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "runtime": "native_comfyui",
            "model_revision": engine.model_revision,
            "qwen_revision": engine.qwen_revision,
        }
        return io.NodeOutput(
            {"waveform": waveform.unsqueeze(0).cpu(), "sample_rate": int(sample_rate)},
            instruction,
            json.dumps(metadata, ensure_ascii=False, indent=2),
            target_seconds,
        )


class AuKAudioTrim(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="AuKAudioTrim",
            display_name="AuK Audio Trim / Duration",
            category="AuK · T8star-Aix",
            description="Trims standard AUDIO in seconds, preserving channels and sample rate. Connect the trimmed audio to AuK Generate / Edit. The source audio is unchanged.",
            inputs=[
                io.Audio.Input("audio", display_name="Source audio"),
                io.Float.Input("start_seconds", display_name="Start (seconds)", default=0.0, min=0.0, step=0.01),
                io.Float.Input("end_seconds", display_name="End (seconds; 0 = end)", default=0.0, min=0.0, step=0.01),
            ],
            outputs=[
                io.Audio.Output("trimmed_audio", display_name="Trimmed audio"),
                io.Float.Output("duration_seconds", display_name="Trimmed duration (seconds)"),
                io.String.Output("info", display_name="Trim details"),
            ],
        )

    @classmethod
    def execute(cls, audio: dict[str, Any], start_seconds: float = 0.0, end_seconds: float = 0.0) -> io.NodeOutput:
        # Reuse validation without returning its mono conversion: trimming must
        # preserve the original channels for PreviewAudio and other nodes.
        if normalize_audio(audio) is None:
            raise ValueError("The trim node requires connected source audio")
        sample_rate = audio["sample_rate"]
        waveform = audio["waveform"]
        start, end = float(start_seconds), float(end_seconds)
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < 0:
            raise ValueError("Trim start and end must be finite, nonnegative seconds")
        total = waveform.shape[-1]
        if start >= total / sample_rate:
            raise ValueError(f"Trim start exceeds source duration {total / sample_rate:.3f}s")
        first = round(start * sample_rate)
        last = total if end == 0 else min(total, round(min(end, total / sample_rate) * sample_rate))
        if first >= total or last <= first:
            raise ValueError(f"Invalid trim range: source duration {total / sample_rate:.3f}s; end must exceed start and start must be within the audio")
        cropped = waveform[..., first:last].detach().to(device="cpu", dtype=torch.float32).clone().contiguous()
        seconds = cropped.shape[-1] / sample_rate
        note = (
            f"Source {total / sample_rate:.3f}s → trim {first / sample_rate:.3f}–{last / sample_rate:.3f}s → "
            f"Actual input {seconds:.3f}s; {sample_rate} Hz, {cropped.shape[1]} channels"
        )
        return io.NodeOutput({"waveform": cropped, "sample_rate": sample_rate}, seconds, note)


class AuKExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [AuKModelLoader, AuKGenerateEdit, AuKAudioTrim]


async def comfy_entrypoint() -> AuKExtension:
    return AuKExtension()
