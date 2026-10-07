# English localization fork

Read [docs/LOCALIZATION.md](docs/LOCALIZATION.md) before translating files or syncing upstream.

## Branch policy

- `upstream`: https://github.com/T8mars/Comfyui-Auk-T8.git
- `origin`: https://github.com/ThisWayLabsAI/Comfyui-Auk-T8.git
- Keep `main` a clean mirror of `upstream/main`; update it only by fast-forward.
- Make English translations, filename renames, and fork maintenance changes on `english-localization`. Check the current branch and working tree before editing.
- Merge updated `main` into `english-localization`. Preserve published history; do not rebase or force-push this branch during routine syncs.
- Preserve unrelated user changes. Do not auto-stash, discard changes, or resolve a diverged `main` with a reset.

## Translation boundaries

- Translate user-visible node names, field labels, tooltips, errors, frontend guides, workflow titles/notes, and documentation to natural English.
- This package uses ComfyUI V3 `io.Schema`. Preserve `node_id`, input/output identifiers, custom data types, slot order, and workflow links. Translate `display_name` and other presentation text.
- Task labels and duration-mode strings are serialized widget values and are used by backend/frontend lookups. Add explicit compatibility for old values when introducing English options; update schemas, lookup code, frontend, examples, and tests together.
- Preserve stable task keys, model paths, checkpoint names, registry identifiers, and API contracts.
- Model instructions and language-specific parser tokens are functional data. Preserve them unless the change is separately justified and validated; do not globally replace Chinese/Korean text.
- Use English filenames for translated project files. Update every reference and record old/new paths in `docs/LOCALIZATION.md`. Preserve upstream sample numbering where applicable.
- Update `tools/generate_example_workflows.py` alongside workflow translations/renames so regeneration preserves English output and does not depend on old paths.
- Keep translations focused; avoid unrelated refactors, dependency changes, or inference behavior changes.

## Maintenance and validation

- Keep filename-only renames separate from content edits when practical, so Git can detect them reliably.
- After every upstream merge, review changed files for newly introduced untranslated UI text, restored filenames, and generator drift. Follow the checks in `docs/LOCALIZATION.md`.
- Preserve old-workflow compatibility and cover it when changing serialized choices. Update language-specific test assertions without weakening behavioral coverage.
- Check JSON validity and workflow structure after workflow changes; run relevant existing tests after backend/frontend changes in the ComfyUI Python environment.
- Record translation decisions, intentional non-English functional strings, and actual filename mappings in the maintenance guide when they change. Do not invent completed work or mark unchecked items verified.
- This document guides agent behavior; it does not enforce Git branch protection or replace validation.
