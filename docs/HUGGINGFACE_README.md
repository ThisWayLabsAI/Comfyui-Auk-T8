---
license: other
language:
- zh
- en
tags:
- audio
- text-to-speech
- voice-cloning
- speech-editing
- comfyui
---

# AuK models and complete Windows package

By T8star-Aix on Bilibili

## Complete Windows package

**[Download AuK-Local.rar](https://huggingface.co/t8star/Auk-Comfy/resolve/main/AuK-Local.rar?download=true)**

- Size: **20,372,471,916 bytes — 20.37 GB (18.97 GiB)**.
- Includes: AuK Local, `AuK-Local.exe`, bundled Python, AuK Base, AuK-Flash, and Qwen2.5-Omni-3B models.
- Fully extract the RAR and double-click `AuK-Local.exe` inside the `AuK-Local` folder. Keep the console open; the browser opens when the service is ready.
- Resume interrupted downloads with a download manager.
- GitHub [AuK Local Releases](https://github.com/T8mars/AuK-Local/releases) provide **code-only updates**, without models or Python.

SHA-256: `a99966c3eb7336ca9d027c0ea491edaddcfa3582b2eb436444a36cfc2f2e9061`

The RAR is the standalone Windows app. For native ComfyUI nodes, install the GitHub node repository and use the model folders below.

This repository contains the models used by the independent [AuK · T8star-Aix native ComfyUI nodes](https://github.com/T8mars/Comfyui-Auk-T8) and by the separate [AuK Local source and releases](https://github.com/T8mars/AuK-Local). The complete local package is available through the Hugging Face download link above, with [Quark Drive](https://pan.quark.cn/s/264edb7e36bd) as an additional download channel.


## Contents

| Folder | Purpose | Upstream source | Pinned revision |
| --- | --- | --- | --- |
| `AuK-Flash` | Four-step speech generation | [tencent/AuK-Flash](https://huggingface.co/tencent/AuK-Flash) | `575b92f0895f75180bf2cbd35f2e176c5732b8ed` |
| `AuK` | Base speech generation and editing | [tencent/AuK](https://huggingface.co/tencent/AuK) | `790742b71a4430120daf2b2099192abae449eb9f` |
| `Qwen2.5-Omni-3B` | Multimodal instruction encoder | [Qwen/Qwen2.5-Omni-3B](https://huggingface.co/Qwen/Qwen2.5-Omni-3B) | `f75b40e3da2003cdd6e1829b1f420ca70797c34e` |

## Native ComfyUI layout

Copy the three folders into `ComfyUI/models/auk`. The native node loads them directly inside ComfyUI and does not require port 7860 or a token.


## Links

- [GitHub nodes](https://github.com/T8mars/Comfyui-Auk-T8)
- [AuK Local source and releases](https://github.com/T8mars/AuK-Local)
- [Bilibili](https://space.bilibili.com/385085361)
- [YouTube](https://www.youtube.com/@T8star-Aix/)
- [API](https://api.seedance.nz/sign-up?aff=5f4w)
- [Online AI apps](https://www.runninghub.ai/zh-cn/user-center/1907375370302308353/userPost?inviteCode=rh-v1121)
- [Standalone local package](https://pan.quark.cn/s/264edb7e36bd)
- [Complete Windows package](https://huggingface.co/t8star/Auk-Comfy/resolve/main/AuK-Local.rar?download=true)
- [Hugging Face profile](https://huggingface.co/t8star)
