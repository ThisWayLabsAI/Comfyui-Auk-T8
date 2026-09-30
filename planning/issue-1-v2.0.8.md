# Issue #1 — short zero-shot voice cloning duration

Issue: [#1](https://github.com/T8mars/Comfyui-Auk-T8/issues/1)

## Fix

The previous native node applied the F5 short-text speed factor (`0.3`) to
both instruction TTS and reference voice cloning. For a target shorter than
10 UTF-8 bytes, such as `不是！`, that produced a 2.4-second target slot.

Version 2.0.8 keeps the existing F5 calculation for instruction TTS and for
longer clone text. For an ultra-short clone target, it uses the unscaled
estimate with a 1.0-second minimum. The node does not request or use a
reference transcript, so it cannot use the upstream reference-text ratio
calculation for this path.

## Verification

- `132 passed` — native-node test suite, including `不是！`, `感谢！`, and `谢谢`.
- `ruff check .` — passed.
- Real AuK Base node run with `不是！`, automatic duration, and a 9.95-second
  reference clip: resolved duration `1.0s`, actual output `1.0s`.
- At a -40 dBFS threshold, the generated output had only leading `0.14s` and
  trailing `0.22s` silence; it contained no internal silent gap.

Generated local audio and metadata are retained outside the repository under
`E:\\auk\\planning\\issue-1-v2.0.8`.
