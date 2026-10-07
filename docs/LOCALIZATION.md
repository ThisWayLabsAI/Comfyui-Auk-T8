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

Task choices currently use Chinese labels in `task_templates.py`; duration choices come from `duration.py`. These values are stored in workflow `widgets_values` and used in execution. English choices need legacy-value compatibility at both workflow loading and execution, coordinated with the frontend and generator. Merely changing visible option strings can invalidate existing workflows.

Chinese model instructions, parser tokens, example utterances tied to source audio, and language-specific duration logic are not automatically presentation text. Preserve their semantics and document intentional non-English functional strings. Do not change model prompts simply to eliminate every non-ASCII character.

## Workflow regeneration and validation

`tools/generate_example_workflows.py` currently reads Chinese-named examples as templates, deletes all `AuK-*.json` examples, and writes the full set again. Update its template paths, filenames, labels, notes, and save prefixes as part of translation work. Do not run it against an uncommitted translation without first reviewing those operations.

For workflow edits, verify every example parses as JSON and retains valid node types, links, slot indices, and widget values. There are currently 17 tasks/examples; preserve full task coverage, adjusting that expectation if upstream adds tasks.

Run existing tests from the repository root with the Python environment that runs ComfyUI and has its dependencies available:

```powershell
python -m pytest
```

The test suite includes workflow coverage and a test that invokes the generator, which rewrites example files. Review `git status` and `git diff` afterward to catch regeneration drift. If the environment cannot run the tests, report the missing dependency or environment limitation; do not describe the change as fully tested.

For interface and serialized-choice changes, also load an old upstream workflow and an English example in ComfyUI. Verify node recognition, task/duration selection, guides, and graph connections. Where inference behavior could be affected, validate an appropriate task using available models and audio; report whether inference was exercised.

## Translation record

Branch setup is complete. At the time this guide was introduced, no node text, workflows, or project filenames had been translated.

### Filename map

No translation renames have been applied yet. Add an exact upstream-path to English-path mapping for each rename, and update imports, README links, tools, and tests that reference it. Keep `AuK-01` through `AuK-17` prefixes for existing examples.

### Intentional non-English functional strings

No per-string inventory has been reviewed yet. Record preserved model instructions, legacy serialized values, parser tokens, and audio-dependent samples as translation work proceeds.

### Sync record

After a sync, record the integrated upstream commit, translation changes needed, validation performed, and any unresolved limitations here. No post-localization upstream sync has been performed yet.
