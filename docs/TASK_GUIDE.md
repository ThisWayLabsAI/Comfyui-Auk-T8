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

## Controls and task-specific limits

- **Base versus Flash:** Base exposes NFE, CFG, and sway. Flash overrides them to `4`, `0`, and `-1`; changing those widgets cannot tune Flash sampling. Compare model variants with the same crop/request rather than assuming their seeds produce equivalent audio.
- **Duration:** TTS can use automatic text estimation or manual duration. Editing follows task rules even when Manual duration is selected. Speech/lyric transcripts assist only their automatic text-length estimate. Speed/emotion/nonverbal edits can expand output beyond 30 seconds, requiring a shorter crop.
- **Voice cloning:** box 1 is new speech, not a reference transcript. Use a clear reference with one speaker; box 2 does not supply extra voice instructions.
- **Lyric editing:** use clean isolated solo a cappella vocals, not a full mixed song. Match sung words exactly.
- **Emotion, accent, whisper:** use ordinary spoken speech. Accent removal is not arbitrary accent conversion, and already-standard speech is not a useful removal test.
- **Separation:** speaker order is relative to the crop. For content-based selection, choose a short phrase unique to the target speaker. Music vocal extraction chooses vocal categories, not a named singer.
- **Volume:** output peak protection may reduce gain to prevent clipping, so a requested boost is not a guarantee of an exact final dB difference.

These controls adjust inference. The node does not train, fine-tune model weights, or load a training adapter. Better instructions, source preparation, model selection, seed exploration, and sampling comparisons are the available tuning methods here.
