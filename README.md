<div align="center">

# AuK · T8star-Aix Native ComfyUI Nodes

Run AuK speech generation and editing directly inside ComfyUI

[Original Chinese documentation](README_CN.md) · [Model repository](https://huggingface.co/t8star/Auk-Comfy) · [Complete Windows package / overseas](https://huggingface.co/t8star/Auk-Comfy/resolve/main/AuK-Local.rar?download=true)

</div>

This fork's `english-localization` branch provides English node labels, task guides, errors, and 17 English-named example workflows. Existing upstream task and duration values remain accepted. See [localization maintenance](docs/LOCALIZATION.md) for upstream sync instructions and the filename map. The original Chinese documentation and historical audit notes are retained for reference.

This is a standalone ComfyUI V3 custom-node package. It loads AuK, AuK-Flash, and Qwen2.5-Omni-3B directly in the ComfyUI process. It does not require AuK Local, a server at `127.0.0.1:7860`, or a service token.

This repository publishes only the **standalone ComfyUI node package**. There is one separate **AuK Local one-click package**. Each can be installed and run independently; they only share model sources and documentation links.

## Nodes

- **AuK Model Loader** defaults to the higher-quality AuK Base and can switch to the speed-oriented AuK-Flash. ComfyUI manages staged loading and offloading of the VAE, Qwen encoder, and DiT.
- **AuK Generate / Edit** exposes 17 English task entries that cover all 16 upstream low-level tasks. Target-speaker extraction is a content-based entry for speaker separation. The node returns standard ComfyUI `AUDIO`, the final instruction, run metadata JSON, and the resolved target duration.
- **AuK Audio Trim / Duration** cuts by start/end seconds while preserving sample rate and channels. It returns cropped `AUDIO`, its exact `FLOAT` duration, and a trim description. An end of `0` means the end of the source.

Tasks include instruction TTS, zero-shot voice cloning, speech and lyric editing, pitch/speed/volume/emotion/timbre editing, de-accenting, nonverbal editing, whisper conversion, enhancement, quality repair, speaker separation, vocal extraction, and target-speaker extraction.

## Install

### ComfyUI Manager

For this English fork, use the Git installation below. The upstream package can be found as **AuK · T8star-Aix** in ComfyUI Manager; installing that package gives you upstream's interface. After updates, confirm that this checkout is still on `english-localization`.

### Git

```bash
cd ComfyUI/custom_nodes
git clone --branch english-localization https://github.com/ThisWayLabsAI/Comfyui-Auk-T8.git
cd Comfyui-Auk-T8
python -m pip install -r requirements.txt
```

Install dependencies with the same Python interpreter that runs ComfyUI. The requirements do not install or replace PyTorch or TorchAudio.

## Models

Download the model files from [t8star/Auk-Comfy](https://huggingface.co/t8star/Auk-Comfy) and keep this layout:

```text
ComfyUI/models/auk/
├── AuK-Flash/
│   ├── auk_flash.safetensors
│   ├── vae.safetensors
│   └── config.yaml
├── AuK/
│   ├── auk_base.safetensors
│   ├── vae.safetensors
│   └── config.yaml
└── Qwen2.5-Omni-3B/
    ├── config.json
    ├── model-00001-of-00003.safetensors
    ├── model-00002-of-00003.safetensors
    ├── model-00003-of-00003.safetensors
    └── the remaining repository files
```

You can also run the downloader with ComfyUI's Python from the node directory. Both model variants require Qwen:

```bash
python download_models.py --variant flash
python download_models.py --variant base
python download_models.py --variant all
```

The downloader is pinned to the tested Hugging Face snapshot recorded in `MODEL_MANIFEST.json` and verifies SHA-256 by default; use `--skip-sha256` only when you intentionally want a faster size-only check. The loader also searches every path registered as `auk` in `extra_model_paths.yaml`; the AuK checkpoint and Qwen folder may be stored in different registered roots.

Flash plus Qwen requires about 18.7 GB. Both AuK variants plus Qwen require about 25.5 GB.

## Run

1. Drag the JSON for the required task from `example_workflows` into ComfyUI. The folder contains an executable workflow for every one of the 17 entries, starting with `AuK-01-Instruction-TTS.json`. Connect your own `auk_input.wav` for source/reference tasks. For speech/lyric edits and target-speaker extraction, replace the sample words with the exact words in your audio.
2. **AuK Model Loader** defaults to AuK Base. Prefer Base for emotion, accent, timbre, nonverbal, whisper, and repair tasks; Flash is intended for fast previews.
3. Select a task in **AuK Generate / Edit**. The node displays task requirements, numbered text-box explanations, examples, and practical tuning tips. Labels and placeholders change with the task. For source/reference tasks, connect `Load Audio → AuK Audio Trim / Duration → AuK Generate / Edit`. Trim long originals before generation. Set both crop values to `0` to pass the full source.
4. Queue the workflow. AuK-Flash always uses NFE=4 and CFG=0; Base uses the advanced sampling controls.

**Automatic duration adaptation:** click **↻ Adapt duration automatically** in the node guide, or select **Automatic adaptation (task rules)** in the visible duration mode widget (the default). Editing uses the actual cropped input and task rules, ignoring a stale target value or a connected Float. No separate Float node is needed. Instruction TTS and voice cloning estimate duration from text. This estimates the spoken length from the target text and prevents a short sentence from continuing into AuK's internal no-reference marker when a much longer duration is requested. Select **Manual duration** for exact TTS timing; editing rules remain automatic. The previous automatic TTS option is kept for existing workflows. Text estimates over 30 seconds now report an error requesting shorter text or separate segments instead of silently truncating. The Seed widget uses ComfyUI's standard **randomize after generation** mode by default; switch its control mode to fixed to reproduce a result. The metadata output records the actual seed, requested duration, resolved duration, and duration mode.

Pitch, volume, timbre, de-accent, and whisper match the effective speech duration measured by official VAD. Enhancement, quality repair, and separation preserve the full input length. Speed uses `effective speech duration / multiplier`. Emotion uses the official factors: 1.22× for sad, 1.16× for fearful, and 1.06× for the other supported emotions. Speech and lyric edits estimate the result from the text added or removed. Nonverbal edits add or remove the official event duration. These automatic rules ignore a stale target-duration widget, so a 48-second source trimmed to four seconds is validated as the actual four-second node input.

Before inference, the node uses official Silero VAD to measure the unpadded speech interval and adds 0.1 seconds only around the model input. Whisper conversion uses the official -44.47 LUFS target; lyric and music-separation outputs use the official -14 LUFS downward limiter and 0.95 peak ceiling. All tasks reject nonfinite audio. If a model peak exceeds the standard audio range, gain is reduced to a 0.99 peak ceiling to prevent FLAC export clipping; ordinary levels and quiet whispers are preserved. Metadata records this protection and its gain in dB. Lyric editing requires clean isolated a cappella solo vocals. Emotion, de-accenting, and whisper conversion require ordinary spoken speech. Singing is not a valid test source for those tasks, and already-standard speech is not a valid de-accenting test. Model loading and generation report native ComfyUI progress through configuration, Qwen, VAE, AuK, text/reference encoding, sampling, and decoding stages. Speed supports `0.5`, `0.75`, `1.25`, `1.5`, or `2.0`; pitch uses `+1/+2/+3` or `-1/-2/-3` semitones, and volume uses `+5/+10/+15` or `-5/-10/-15` dB.

Source/reference audio and generated output are each limited to 30 seconds independently. They are not added together, so a 30-second input may produce a 30-second output. Slowing speech or changing emotion may resolve to more than 30 seconds; trim the source first in that case. VAD removes some leading/trailing silence in speech tasks. Metadata separately records the cropped raw input, prepared input, and resolved output duration. CPU mode is available for compatibility testing but is very slow; NVIDIA CUDA with bf16 is recommended.

> Version 2.0.7 adds a clickable automatic-duration button and a standalone audio-trim node, connected in every audio workflow. Input validation uses exact sample counts for the 30-second limit, rejects invalid sampling parameters, and exposes the resolved target duration. Restart ComfyUI and reload the browser after upgrading. Add the crop node to an old graph or import a new workflow.

> Version 2.0.8 fixes automatic duration for ultra-short zero-shot voice-cloning targets. Two-character Chinese lines such as `不是！` now resolve to 1.0 second instead of applying the F5 short-text slowdown and creating a long padded slot. Longer clone targets and instruction TTS keep their existing duration rules.

> Version 2.0.6 fixes validation against stale pre-trim durations and applies independent 30-second limits to input and output. It completes the official duration and preprocessing rules, adds quality repair, and defaults to AuK Base. The package includes drag-and-drop workflows for all 17 task entries.

> Version 2.0.6 uses official unpadded Silero speech duration and LUFS handling, validates nonverbal/quality/speaker-order requests before inference, and displays the matching official guide inside the node.

## Text boxes and better speech edits

See the [task input and tuning guide](docs/TASK_GUIDE.md) for all 17 tasks. The second text box is **not a general additional-instructions prompt**. For speech/lyric edits it accepts an optional transcript of the cropped source, used only for duration estimation. Most tasks ignore it; instruction TTS uses it for voice description, and speaker extraction uses it for supported cleanup keywords.

For speech text editing, start with **AuK Base**, crop to the sentence with a little surrounding context, and enter one precise request in box 1, for example `Replace 'Los Angeles' with 'Florida'.` Use the exact words spoken in your crop. Box 2 can contain the full original transcript of that crop, before replacement. Try a few seeds, then fix the seed before comparing settings. Base defaults are NFE `32`, CFG `2`, sway `-1`; experiment with one control at a time. Flash forces NFE `4`, CFG `0`, and a fixed sampling time grid, ignoring the displayed sampling values. These are inference adjustments, not training or weight fine-tuning.

The node's expandable **Seed, sampling & duration** help explains each control for the selected task and updates its tooltips. Seeds affect both Base and Flash; higher seed numbers are not better. NFE is sampling effort, CFG is extra conditioning guidance (not a gain/speed/edit-strength knob), and sway redistributes sampling steps rather than choosing a location in the audio. See [control explanations and per-task listening checks](docs/TASK_GUIDE.md#seed-nfe-cfg-sway-and-duration). The sampling mechanism is shared across tasks; no task-specific optimal presets or guaranteed quality improvements are claimed.

Restart ComfyUI and refresh the browser after updating to load new backend tooltips and frontend guides. Older workflows retain their text and graph connections; task changes update help without clearing text, so review both boxes when switching tasks.

## Troubleshooting installation

### Missing model configuration

Checkpoint weights alone are not enough. Both `AuK/` and `AuK-Flash/` need their own `config.yaml`; the Qwen folder needs its tokenizer, processor, configuration, and all three weight shards. Use the downloader above, or obtain the matching configs from the pinned snapshot: [Base config](https://huggingface.co/t8star/Auk-Comfy/resolve/326a675046f653f4df2eed89ac3195b028db1749/AuK/config.yaml), [Flash config](https://huggingface.co/t8star/Auk-Comfy/resolve/326a675046f653f4df2eed89ac3195b028db1749/AuK-Flash/config.yaml). Save each in the corresponding model directory, not the custom-node directory.

### `ModuleNotFoundError: No module named 'qwen_omni_utils'`

Qwen audio processing needs this dependency even when the models load successfully. Install it into **ComfyUI's Python**, not an unrelated system Python. For this Windows embedded layout (adjust the path for your installation):

```powershell
& "C:\ComfyUI-Easy-Install\python_embeded\python.exe" -m pip install "qwen-omni-utils==0.0.9"
& "C:\ComfyUI-Easy-Install\python_embeded\python.exe" -c "from qwen_omni_utils import process_mm_info; print('Qwen audio utilities OK')"
```

Restart ComfyUI after installation. The reported installation was repaired with `--no-deps` **only after verifying the package's dependencies were already installed**; do not use that flag on an incomplete environment. On an existing shared ComfyUI installation, review dependency changes before reinstalling the full requirements: this package's Transformers pin can change an already installed version. Installing the missing package does not require replacing PyTorch or installing FlashAttention.

### `flash_attn.bert_padding` import error with SeedVR2

Some SeedVR2 installations register an incomplete `flash_attn` placeholder. Earlier AuK code mistook it for a working FlashAttention installation. This fork guards optional imports and continues with its PyTorch attention backend. Update this fork and restart ComfyUI; installing FlashAttention is not required for the default AuK inference path. **AuK-Flash**, the model variant, is separate from **FlashAttention**, the optional attention library.

## Standalone local package

**Complete AuK Local Windows package (models and Python included): [Hugging Face overseas download — AuK-Local.rar](https://huggingface.co/t8star/Auk-Comfy/resolve/main/AuK-Local.rar?download=true)**, 20.37 GB (18.97 GiB). Fully extract it and double-click `AuK-Local.exe` in the `AuK-Local` folder. GitHub AuK Local Release ZIPs contain program updates only.

The [AuK Local one-click package](https://pan.quark.cn/s/264edb7e36bd) remains a separate light-themed web workstation with its own Python runtime, model management, task history, and launch scripts. It is no longer a runtime prerequisite for these ComfyUI nodes.

## Compatibility

- ComfyUI `>=0.23.0` with the V3 custom-node API and staged model-management interfaces.
- Python `>=3.10`.
- Verified with PyTorch/TorchAudio 2.7.x + CUDA 12.8 and a 24 GB NVIDIA GPU.
- Model construction uses substantial host memory; 48 GB or more system RAM is recommended.
- Output is 24 kHz float audio.

## Links

- [Bilibili](https://space.bilibili.com/385085361)
- [YouTube](https://www.youtube.com/@T8star-Aix/)
- [API](https://api.seedance.nz/sign-up?aff=5f4w)
- [Online AI apps](https://www.runninghub.ai/zh-cn/user-center/1907375370302308353/userPost?inviteCode=rh-v1121)
- [Standalone local package](https://pan.quark.cn/s/264edb7e36bd)
- [AuK-Comfy models](https://huggingface.co/t8star/Auk-Comfy)
- [Hugging Face profile](https://huggingface.co/t8star)
- [Original AuK project](https://github.com/Tencent-Hunyuan/AuK)

## License

The node code is released under the [MIT License](LICENSE). Model files retain the licenses included by their upstream repositories.
