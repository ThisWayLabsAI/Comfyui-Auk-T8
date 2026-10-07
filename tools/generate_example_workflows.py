from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "example_workflows"

TASK_DATA = runpy.run_path(str(ROOT / "task_templates.py"))
TASK_BY_KEY = TASK_DATA["TASK_BY_KEY"]

# Number, stable task key, primary sample, optional transcript/description, filename.
EXAMPLES = (
    ("01", "instruct_tts", "Hello, welcome to the native AuK ComfyUI nodes.", "A natural, clear, warm young female voice", "Instruction-TTS"),
    ("02", "zero_shot_tts", "Hello, this is a test using the reference voice.", "", "Voice-Cloning"),
    ("03", "content_edit", "Replace 'this afternoon' with 'tomorrow morning'.", "The meeting is this afternoon. Please arrive on time.", "Speech-Text-Editing"),
    ("04", "lyric_edit", "Change 'hello tomorrow' to 'hello future' in the vocal recording.", "Hello tomorrow, how small our voices are.", "Lyric-Editing"),
    ("05", "pitch", "+1", "", "Pitch-Editing"),
    ("06", "speed", "1.25", "", "Speed-Editing"),
    ("07", "volume", "+5", "", "Volume-Editing"),
    ("08", "emotion", "sad", "", "Emotion-Editing"),
    ("09", "timbre", "A deep, resonant young male voice", "", "Timbre-Editing"),
    ("10", "deaccent", "Remove the regional accent", "", "Accent-Removal"),
    ("11", "nonverbal", "Add laughter after 'welcome back'.", "", "Nonverbal-Sound-Editing"),
    ("12", "whisper", "Convert to whisper", "", "Whisper-Conversion"),
    ("13", "enhance", "Remove noise and room reverb", "", "Speech-Enhancement"),
    ("14", "quality", "Restore high frequencies and clarity", "", "Audio-Quality-Repair"),
    ("15", "speech_separate", "The first speaker", "", "Speaker-Separation"),
    ("16", "music_separate", "Keep only singing vocals", "", "Music-Vocal-Extraction"),
    ("17", "target_speaker", "Welcome to today's program", "", "Target-Speaker-Extraction"),
)

OUTPUT_NAMES = {
    "AuKModelLoader": ("AuK Model",),
    "AuKGenerateEdit": ("Generated audio", "Final instruction", "Run metadata JSON", "Resolved target duration (seconds)"),
    "AuKAudioTrim": ("Trimmed audio", "Trimmed duration (seconds)", "Trim details"),
}


def main() -> None:
    if {entry[1] for entry in EXAMPLES} != set(TASK_BY_KEY):
        raise ValueError("Example coverage differs from task definitions; update the English examples")
    expected_paths = {WORKFLOW_DIR / f"AuK-{number}-{filename}.json" for number, _, _, _, filename in EXAMPLES}
    unexpected = set(WORKFLOW_DIR.glob("AuK-*.json")) - expected_paths
    if unexpected:
        raise ValueError(f"Unexpected workflow paths; reconcile upstream renames first: {sorted(map(str, unexpected))}")
    no_audio = json.loads((WORKFLOW_DIR / "AuK-01-Instruction-TTS.json").read_text(encoding="utf-8"))
    with_audio = json.loads((WORKFLOW_DIR / "AuK-03-Speech-Text-Editing.json").read_text(encoding="utf-8"))
    duration_data = runpy.run_path(str(ROOT / "duration.py"))
    for number, key, primary, secondary, filename in EXAMPLES:
        task = TASK_BY_KEY[key]
        label, needs_audio = task.label, task.needs_audio
        workflow = copy.deepcopy(with_audio if needs_audio else no_audio)
        loader = next(node for node in workflow["nodes"] if node["type"] == "AuKModelLoader")
        generator = next(node for node in workflow["nodes"] if node["type"] == "AuKGenerateEdit")
        saver = next(node for node in workflow["nodes"] if node["type"] == "SaveAudio")
        loader["widgets_values"] = ["AuK Base", "auto", "auto"]
        generator["widgets_values"] = [
            label,
            primary,
            secondary,
            3.0,
            42,
            "randomize",
            32,
            2.0,
            -1.0,
            duration_data["AUTO_TASK_DURATION_MODE"],
        ]
        generator["size"] = [520, 640]
        if not any(output.get("type") == "FLOAT" for output in generator["outputs"]):
            generator["outputs"].append({
                "name": "Resolved target duration (seconds)", "type": "FLOAT", "links": None, "slot_index": 3,
            })
        saver["widgets_values"] = [f"auk/{filename}"]
        if needs_audio:
            audio_loader = next(node for node in workflow["nodes"] if node["type"] == "LoadAudio")
            audio_loader["widgets_values"] = ["auk_input.wav"]
            workflow["nodes"] = [node for node in workflow["nodes"] if node["type"] != "AuKAudioTrim"]
            audio_loader["pos"] = [40, 290]
            audio_loader["outputs"][0]["links"] = [2]
            generator["inputs"][1]["link"] = 5
            generator["order"] = 3
            workflow["nodes"].append({
                "id": 6, "type": "AuKAudioTrim", "pos": [40, 540], "size": [390, 150],
                "flags": {}, "order": 2, "mode": 0,
                "inputs": [{"name": "audio", "type": "AUDIO", "link": 2}],
                "outputs": [
                    {"name": "Trimmed audio", "type": "AUDIO", "links": [5], "slot_index": 0},
                    {"name": "Trimmed duration (seconds)", "type": "FLOAT", "links": None, "slot_index": 1},
                    {"name": "Trim details", "type": "STRING", "links": None, "slot_index": 2},
                ],
                "properties": {"Node name for S&R": "AuKAudioTrim"},
                "widgets_values": [0.0, 0.0],
            })
            workflow["links"] = [
                [1, 1, 0, 3, 0, "AUK_ENGINE"], [2, 2, 0, 6, 0, "AUDIO"],
                [3, 3, 0, 4, 0, "AUDIO"], [4, 3, 0, 5, 0, "AUDIO"], [5, 6, 0, 3, 1, "AUDIO"],
            ]
            workflow["last_node_id"], workflow["last_link_id"] = 6, 5
            for node in workflow["nodes"]:
                if node["type"] == "PreviewAudio":
                    node["order"] = 4
                elif node["type"] == "SaveAudio":
                    node["order"] = 5
        for node in workflow["nodes"]:
            if node["type"].startswith("AuK"):
                node["properties"].update({"cnr_id": "auk-t8", "ver": "2.0.8"})
                for output, name in zip(node["outputs"], OUTPUT_NAMES[node["type"]]):
                    output["name"] = name
        path = WORKFLOW_DIR / f"AuK-{number}-{filename}.json"
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Keep frontend guides and migration aliases derived from the backend definitions.
    guides = {}
    for task in TASK_DATA["TASKS"]:
        guide = TASK_DATA["TASK_GUIDES"][task.key]
        guides[task.label] = {
            "key": task.key,
            "primary_label": task.primary_label,
            "secondary_label": task.secondary_label,
            "requirement": guide.requirement,
            "example": guide.example,
            "note": guide.note,
        }
    (ROOT / "web" / "task_guides.json").write_text(
        json.dumps(guides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    aliases = {
        "task": {label: TASK_BY_KEY[key].label for label, key in TASK_DATA["LEGACY_TASK_LABELS"].items()},
        "duration_mode": duration_data["DURATION_MODE_ALIASES"],
    }
    (ROOT / "web" / "legacy_widget_values.json").write_text(
        json.dumps(aliases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
