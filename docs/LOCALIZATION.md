# English localization maintenance

This fork maintains English node interfaces, example workflows, documentation, and project filenames while continuing to receive upstream fixes.

## Repository and branch ownership

| Reference | Purpose |
| --- | --- |
| `upstream/main` | Original project at `T8mars/Comfyui-Auk-T8` |
| `origin/main` and local `main` | Clean mirror of upstream |
| `origin/english-localization` and local `english-localization` | English translations and fork maintenance |

The installed checkout should remain on `english-localization` to use the translated files. Switching branches changes the files ComfyUI loads; restart ComfyUI and refresh the browser after changing the installed code.

Do not merge localization into the fork's `main` as part of routine maintenance. These instructions do not configure GitHub protections or control updates performed by ComfyUI Manager; check the branch and working tree after external update tools run.

## Routine upstream sync

Start with a clean working tree. If there are pending changes, finish and commit them or stop to decide how to preserve them. Inspect the remotes and fetch both repositories:

```powershell
git status --short --branch
git remote -v
git fetch origin
git fetch upstream
git switch main
git merge --ff-only origin/main
git merge --ff-only upstream/main
git rev-list --left-right --count main...upstream/main
```

Run commands one at a time and stop on any error. The count must be `0 0` before publishing `main`. A fast-forward failure or any commits unique to `main` requires investigation; do not reset or force-push to make the check pass.

```powershell
git push origin main
git switch english-localization
git merge --ff-only origin/english-localization
git rev-parse HEAD
git merge main
```

Record the hash from `git rev-parse HEAD` as `<pre-sync-hash>` for the review below. If the translation branch and its remote have diverged, inspect their commits and reconcile them before continuing. Do not rebase published localization history.

If merging `main` produces conflicts, use `git status` and resolve each file by preserving upstream behavior and applying the English presentation to it. For renamed examples, consult the filename map below and carry upstream edits to the English path. Do not accept an entire side automatically. Stage the resolved files and run `git merge --continue`; `git merge --abort` cancels an unresolved merge if needed.

Review and validate before publishing the translation branch:

```powershell
git diff --name-status <pre-sync-hash> HEAD
git diff <pre-sync-hash> HEAD -- nodes.py duration.py task_templates.py web tools example_workflows
git diff --check
git status --short --branch
```

Angle-bracket placeholders must be replaced with the recorded hash. Check upstream additions for untranslated labels, notes, errors, changed task options, and renamed/recreated files. Apply needed translations as focused follow-up commits, perform the relevant checks below, then publish:

```powershell
git push origin english-localization
```

## Compatibility rules

The nodes use ComfyUI V3 `io.Schema`, rather than legacy `NODE_CLASS_MAPPINGS`. Preserve `AuKModelLoader`, `AuKGenerateEdit`, and `AuKAudioTrim` node IDs, input/output identifiers, `AUK_ENGINE`, slot order, and graph links. Human-facing `display_name`, tooltips, and guides can be translated.

Task choices now use English labels in `task_templates.py`; duration choices come from `duration.py`. `LEGACY_TASK_LABELS` and `DURATION_MODE_ALIASES` preserve the Chinese values stored in upstream workflows and API requests. Schemas accept both languages so server validation remains compatible. `web/js/auk_task_controls.js` migrates loaded values to English and removes legacy entries from visible option lists using generated `web/legacy_widget_values.json`.

Chinese model instructions, parser tokens, example utterances tied to source audio, and language-specific duration logic are not automatically presentation text. Preserve their semantics and document intentional non-English functional strings. Do not change model prompts simply to eliminate every non-ASCII character.

## Workflow regeneration and validation

`tools/generate_example_workflows.py` reads the English Instruction TTS and Speech Text Editing examples as templates and rewrites the 17 known English examples. It also regenerates `web/task_guides.json` and `web/legacy_widget_values.json` from backend definitions. It rejects unexpected `AuK-*.json` paths or changed task coverage before writing; reconcile upstream additions/renames rather than deleting them blindly. Review its rewrites before running against uncommitted workflow edits.

```powershell
python tools/generate_example_workflows.py
```

For workflow edits, verify every example parses as JSON and retains valid node types, links, slot indices, and widget values. There are currently 17 tasks/examples; preserve full task coverage, adjusting that expectation if upstream adds tasks.

Run existing tests from the repository root with the Python environment that runs ComfyUI and has its dependencies available:

```powershell
python -m pytest
node --test tests/test_task_controls.cjs
```

The test suite includes workflow coverage and a test that invokes the generator, which rewrites example files. Review `git status` and `git diff` afterward to catch regeneration drift. If the environment cannot run the tests, report the missing dependency or environment limitation; do not describe the change as fully tested.

For interface and serialized-choice changes, also load an old upstream workflow and an English example in ComfyUI. Verify node recognition, task/duration selection, guides, and graph connections. Where inference behavior could be affected, validate an appropriate task using available models and audio; report whether inference was exercised.

## Translation record

English localization was implemented on October 7, 2026, based on upstream commit `c40eee27dbc6effcf8b235d6e44f9a49abe2a30e` (2.0.8). All three node schemas, 17 task guides/options, duration controls, wrapper errors, example filenames/contents, save prefixes, and primary English documentation are translated. Node IDs, task keys, graph wiring, model files, and canonical model instructions are preserved.

English parser support was added for the documented edit requests, whisper directions, cleanup/repair requests, vocal selection, speaker order, and nonverbal placement. For audio-dependent tasks, replace example words and transcripts with the actual source words; examples still load user-supplied `auk_input.wav`.

### Filename map

All paths below are relative to `example_workflows/`. The generator and English README use these names. Renames were saved separately from content translations for Git's rename detection.

| Upstream filename | English filename |
| --- | --- |
| `AuK-01-描述生成语音.json` | `AuK-01-Instruction-TTS.json` |
| `AuK-02-参考声音克隆.json` | `AuK-02-Voice-Cloning.json` |
| `AuK-03-语音文字编辑.json` | `AuK-03-Speech-Text-Editing.json` |
| `AuK-04-歌词编辑.json` | `AuK-04-Lyric-Editing.json` |
| `AuK-05-音高编辑.json` | `AuK-05-Pitch-Editing.json` |
| `AuK-06-速度编辑.json` | `AuK-06-Speed-Editing.json` |
| `AuK-07-音量编辑.json` | `AuK-07-Volume-Editing.json` |
| `AuK-08-情绪编辑.json` | `AuK-08-Emotion-Editing.json` |
| `AuK-09-音色编辑.json` | `AuK-09-Timbre-Editing.json` |
| `AuK-10-去口音.json` | `AuK-10-Accent-Removal.json` |
| `AuK-11-非语言声音编辑.json` | `AuK-11-Nonverbal-Sound-Editing.json` |
| `AuK-12-耳语转换.json` | `AuK-12-Whisper-Conversion.json` |
| `AuK-13-语音增强.json` | `AuK-13-Speech-Enhancement.json` |
| `AuK-14-音质修复.json` | `AuK-14-Audio-Quality-Repair.json` |
| `AuK-15-说话人分离.json` | `AuK-15-Speaker-Separation.json` |
| `AuK-16-音乐人声提取.json` | `AuK-16-Music-Vocal-Extraction.json` |
| `AuK-17-指定说话人提取.json` | `AuK-17-Target-Speaker-Extraction.json` |

### Intentional non-English functional strings

- `task_templates.py`: canonical Chinese AuK model prompts, Chinese request parsing/ordinal tables, and emotion/event aliases remain functional. English requests map to the existing canonical prompts where appropriate.
- `duration.py`: Chinese legacy duration values remain accepted; CJK detection and byte-based duration heuristics retain upstream behavior.
- `preprocess.py`: Chinese whisper-direction tokens remain supported alongside English equivalents.
- `web/legacy_widget_values.json`: Chinese keys intentionally migrate serialized upstream values to English.
- `README_CN.md`, `planning/`, and existing Chinese test inputs preserve original documentation, historical evidence, and multilingual compatibility coverage. The Chinese example in the English README's 2.0.8 release note illustrates a duration regression.
- `auk_core/`: model math and canonical prompts are preserved, including a Chinese developer TODO. A fork compatibility fix guards optional FlashAttention imports against incomplete placeholders registered by other custom nodes; the inference path continues to use PyTorch attention. Model/config/registry identifiers are unchanged.

### Runtime compatibility fixes

- October 7, 2026: `AuKModelLoader` reached model import after the missing variant `config.yaml` files were supplied. SeedVR2's compatibility module registers a `flash_attn` placeholder when FlashAttention is unavailable. AuK's package-presence check accepted that placeholder, then failed importing `flash_attn.bert_padding`, despite inference selecting the PyTorch backend. The optional import now tolerates incomplete/unloadable FlashAttention and rejects an explicit FlashAttention selection with a clear error. A subprocess regression test reproduces the placeholder, checks PyTorch attention execution, and imports the actual inference entrypoint without loading weights. Recheck this guard during upstream syncs.

### Sync record

After each sync, record the integrated upstream commit, translation updates, checks performed, and unresolved limitations here. No subsequent upstream release has been merged yet.

### Initial validation

Validation passed: 165 Python tests and 2 frontend Node tests. The suite ran in ComfyUI's embedded Python; pytest was loaded from the existing Hermes environment without installing or modifying dependencies. The frontend tests exercise all 17 legacy task mappings, English option lists, automatic-duration controls, and metadata loading before/after node creation. The generator idempotence test covers workflows and both generated metadata files. JavaScript syntax, JSON/graph coverage, and whitespace checks passed.

Live ComfyUI browser loading and real model inference have not been exercised in this session. The existing service on port 8188 still reports the pre-translation Chinese node definition; restart ComfyUI and refresh the browser to load this code. Automated execution tests use a fake engine; unchanged Chinese model prompts are intentional, but English sample audio quality still requires an inference check.
