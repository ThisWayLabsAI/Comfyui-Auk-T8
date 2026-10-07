# AuK task inputs and inference tuning

Select the task first. The node's pink **Usage & tuning** panel, numbered text-box labels, placeholders, and tooltips explain that task. Switching tasks does not clear existing text: replace leftover requests yourself. Stable input names remain `primary` and `secondary` for workflow/API compatibility.

## What the two text boxes do

| Task | Box 1: primary text | Box 2: secondary text |
| --- | --- | --- |
| Instruction TTS | Words to speak | Voice/style description used in the prompt |
| Voice Cloning | New words to speak in the reference voice | Unused; leave blank |
| Speech Text Editing | One exact replacement, insertion, or deletion request | Optional full **original cropped-source transcript**, for duration estimation only |
| Lyric Editing | One exact lyric replacement | Optional full **original cropped-source lyrics**, for duration estimation only |
| Pitch Editing | Signed semitones: `+1`, `+2`, `+3`, `-1`, `-2`, `-3` | Unused; leave blank |
| Speed Editing | Multiplier: `0.5`, `0.75`, `1.25`, `1.5`, `2.0` | Unused; leave blank |
| Volume Editing | Signed dB: `+5`, `+10`, `+15`, `-5`, `-10`, `-15` | Unused; leave blank |
| Emotion Editing | `happy`, `angry`, `sad`, `fearful`, `surprised`, `disgusted`, `calm`, or `excited` | Unused; leave blank |
| Timbre Editing | Concise description of the desired voice | Unused; leave blank |
| Accent Removal | Nonempty request, e.g. `Remove the regional accent` (fixed model action) | Unused; neither box chooses a target language/accent |
| Nonverbal Sound Editing | Event and location, e.g. `Add laughter after 'welcome back'` | Unused; leave blank |
| Whisper Conversion | `Convert to whisper` or `Convert to normal speech` | Unused; leave blank |
| Speech Enhancement | Remove noise, room reverb, or both | Unused; leave blank |
| Audio Quality Repair | Defect/repair request, e.g. `Remove the telephone effect` | Unused; leave blank |
| Speaker Separation | Order of first speech in the **cropped** audio, e.g. `The second speaker` | Optional `denoise`, `dereverb`, or both |
| Music Vocal Extraction | `Keep only singing vocals` or `Keep all vocals` | Unused; leave blank |
| Target-Speaker Extraction | Exact phrase **already spoken** by the desired speaker | Optional `denoise`, `dereverb`, or both |

The second box is not a general-purpose instruction prompt. In speech/lyric editing it neither corrects recognition nor tells the model what to say. Do not enter the final edited transcript there. For speaker tasks, arbitrary style prose is not supported cleanup. Task-specific examples in the node use the formats supported by this fork; canonical model instructions are preserved. The [upstream AuK cookbook](https://github.com/Tencent-Hunyuan/AuK/blob/main/docs/COOKBOOK.md) provides model-level task context, but its separate UI/API duration behavior is not necessarily this fork's behavior.

## Speech text editing: improve an almost-right result

1. Use **AuK Base** and clean spoken audio. Trim to the relevant sentence with a little context on either side. Keep input and resolved output within their separate 30-second limits.
2. Match the source exactly. In box 1 use one request such as `Replace 'Los Angeles' with 'Florida'.` If the same words occur more than once, use a longer unique phrase. Do not combine several edits or append unrelated style directions.
3. In box 2, optionally supply the complete original transcript of that **crop**, including unchanged words. For example, if the crop says “I'm flying to Los Angeles tomorrow,” use that entire original sentence, not “I'm flying to Florida tomorrow.” The transcript helps the duration heuristic account for how much of the clip is changing; it does not guarantee better pronunciation.
4. Start with Base defaults: NFE `32`, CFG `2`, sway `-1`. Try a few seeds first. Keep a promising seed fixed using the seed's control mode, then compare one setting at a time. Record the instruction, seed, and metadata outputs so comparisons are reproducible.
5. As experiments, compare NFE `48` or `64`, or modest CFG changes such as `1.5` and `2.5`. More steps or stronger guidance do not guarantee a more accurate edit. Leave sway at `-1` while evaluating the other controls. Listen for correct words, voice continuity, timing, and artifacts, not only whether the right location changed.
6. If the edit still fails, simplify the crop or replacement and try another seed. A longer replacement can need more time. The returned resolved duration shows the actual automatic estimate; a manual duration value or connected Float does **not** override editing duration in this fork.

The model can alter surrounding audio while regenerating the crop; it is not a sample-exact splice editor. If untouched audio must remain identical, edit a short crop and reassemble it in an audio editor, checking boundaries and using crossfades where appropriate.

## Seed, NFE, CFG, sway, and duration

The sampling mechanism is shared across tasks. There is no separate, validated best NFE/CFG/sway preset for each task in this fork. Task-specific advice below changes what you evaluate, not the underlying control definitions. These listening checks and suggested comparisons are experiments, not promises of better output.

| Control | What it changes | How to compare |
| --- | --- | --- |
| Seed | Starting noise for generation; can change words, delivery, voice character, and artifacts | Try several seeds with the same request/crop/settings. A larger number is not better. Record a promising seed, then choose **fixed** in control after generate before comparing controls. Seeds affect Base and Flash. |
| NFE steps | Number of sampling steps along the noise-to-audio process, not repeated editing attempts | Base starts at `32`; compare `48` or `64` if needed. More steps cost time and do not guarantee improved quality or complete replacement. Flash always uses `4`. |
| CFG strength | Extra guidance toward instruction and reference-audio conditioning | Base starts at `2`; compare `1.5`, `2`, and `2.5` with the same fixed seed. Higher values may strengthen conditioning but can sound unnatural or introduce artifacts. **CFG 0 still uses the instruction/reference**; it removes the extra guidance boost. Flash always uses `0`. |
| Sway coefficient | Distribution of steps along sampling, not positions in the recording | `0` gives evenly spaced sampling times; negative values concentrate steps earlier in the noise-to-audio process. Leave Base at `-1` while comparing seeds, CFG, and NFE. Flash ignores the widget and uses a fixed sampling time grid. |
| Duration adaptation | Available generated audio length and therefore the timing/pacing constraint | TTS supports automatic target-text estimation or manual target seconds. Every editing task follows its automatic task rules even when Manual duration is selected. Check **Resolved target duration** and metadata rather than the stale target-seconds widget. |

The [upstream sampler](https://github.com/Tencent-Hunyuan/AuK/blob/main/src/auk/model/cfm_edit.py) shows the seed, guidance, and sampling-time mechanisms; this fork's `runtime.py` and `nodes.py` define its Flash overrides and duration behavior. Sampling controls do not train weights, select an edit region, or guarantee exact pronunciation.

### A useful comparison order

1. Start with Base `NFE=32`, `CFG=2`, `sway=-1`, a suitable crop, and a valid task request.
2. Explore several seeds with all other inputs unchanged. The user reported meaningful seed variation during speech editing; this is not evidence of a task-wide optimal seed.
3. Fix a promising seed. Compare CFG `1.5/2/2.5`, then compare NFE `32/48/64` at the best CFG. Leave sway unchanged initially.
4. Save the actual seed, model, crop, instruction, settings, resolved duration, and output. Randomize-after-generation changes the widget for the next run; metadata records the seed actually used.

The same seed is useful for controlled comparisons, but changing the crop, duration, request, settings, model, or software/hardware can change the result. It is not a guarantee of identical audio across environments. For important comparisons, repeat promising settings with a few seeds rather than judging everything from one lucky result.

### What to evaluate for each task

Use the shared Base starting point above for these experiments; no task-specific optimal numeric presets are claimed. The node's expandable **Seed, sampling & duration** help and control tooltips show the corresponding guidance when you select a task.

| Task | Listen for when comparing seeds/NFE/CFG | Duration in this fork |
| --- | --- | --- |
| Instruction TTS | Correct words, pauses, requested voice/style, natural delivery | Automatic from target text; manual target seconds supported |
| Voice Cloning | New-word pronunciation, reference-speaker resemblance, pacing; CFG is not a similarity slider | Automatic from new target text; manual target seconds supported |
| Speech Text Editing | Complete replacement, unchanged words, voice continuity, artifacts | Automatic source/edit estimate; optional full original cropped transcript assists the estimate |
| Lyric Editing | Correct sung replacement, preserved melody and voice | Automatic source/lyric estimate; optional original cropped lyrics assist the estimate |
| Pitch Editing | Requested shift, intact words, voice artifacts; NFE/CFG do not set semitones | Effective source speech duration |
| Speed Editing | Intelligibility, rhythm, voice continuity; NFE/CFG do not set speed | Effective speech duration divided by requested multiplier |
| Volume Editing | Loudness, clarity, clipping; CFG is not gain and peak protection may reduce boosts | Effective source speech duration |
| Emotion Editing | Requested emotion with retained words/identity; CFG is not calibrated emotion intensity | Effective speech duration multiplied by `1.22` for sad, `1.16` for fearful, `1.06` for others |
| Timbre Editing | Requested voice character without losing words; CFG is not an exact voice-match control | Effective source speech duration |
| Accent Removal | Accent reduction, retained words and identity; sampling does not choose another language/accent | Effective source speech duration |
| Nonverbal Sound Editing | Event sound/placement and intact nearby speech; sampling does not set exact event length | Source speech duration plus/minus an event-family allowance |
| Whisper Conversion | Clear words and correct delivery; quiet whisper output is intentional | Effective source speech duration |
| Speech Enhancement | Residual noise/reverb versus missing speech and voice coloration | Full cropped input length, including silence |
| Audio Quality Repair | Restored clarity versus invented/lost detail and new artifacts | Full cropped input length, including silence |
| Speaker Separation | Desired-speaker completeness versus other-speaker leakage; CFG does not select the speaker | Full cropped input length, including silence |
| Music Vocal Extraction | Vocal completeness versus accompaniment leakage/distortion; CFG does not choose a named singer | Full cropped input length, including silence |
| Target-Speaker Extraction | Target-speaker completeness versus leakage; ensure the identifying phrase is correct first | Full cropped input length, including silence |

All editing rows ignore manual target seconds and a connected Float. Source and output are each limited to 30 seconds independently. Timing estimates are heuristic: supplying a transcript can improve timing, but it does not become another model instruction or force the final words.

### Partial multi-word replacement

If `Replace 'Los Angeles' with 'Florida'.` produces “Florida Angeles,” try a larger phrase containing nearby unchanged words, such as `Replace 'let them take out Los Angeles' with 'let them take out Florida'.` Keep the full original cropped transcript, including repetitions, in box 2. Compare short and expanded requests with a fixed seed, then explore seeds if needed. This is a boundary-clarifying experiment, not a guaranteed fix; extra instructions in box 2 cannot force removal of the leftover word.

## Task-specific limits

- **Base versus Flash:** Base exposes NFE, CFG, and sway. Flash forces NFE `4`, CFG `0`, and a fixed time grid; metadata reports sway `-1`, but the widget is ignored in Flash sampling. Compare model variants with the same crop/request rather than assuming their seeds produce equivalent audio.
- **Duration:** TTS can use automatic text estimation or manual duration. Editing follows task rules even when Manual duration is selected. Speech/lyric transcripts assist only their automatic text-length estimate. Speed/emotion/nonverbal edits can expand output beyond 30 seconds, requiring a shorter crop.
- **Voice cloning:** box 1 is new speech, not a reference transcript. Use a clear reference with one speaker; box 2 does not supply extra voice instructions.
- **Lyric editing:** use clean isolated solo a cappella vocals, not a full mixed song. Match sung words exactly.
- **Emotion, accent, whisper:** use ordinary spoken speech. Accent removal is not arbitrary accent conversion, and already-standard speech is not a useful removal test.
- **Separation:** speaker order is relative to the crop. For content-based selection, choose a short phrase unique to the target speaker. Music vocal extraction chooses vocal categories, not a named singer.
- **Volume:** output peak protection may reduce gain to prevent clipping, so a requested boost is not a guarantee of an exact final dB difference.

These controls adjust inference. The node does not train, fine-tune model weights, or load a training adapter. Better instructions, source preparation, model selection, seed exploration, and sampling comparisons are the available tuning methods here.
