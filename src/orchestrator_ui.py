"""
Custom Pika-style UI. This is the app you actually open on your phone —
it is a separate Gradio app from Wan2GP's own UI, launched with its own
public share link from the notebook's final cell.
"""

import os
import time

import gradio as gr

from story_splitter import split_story
from tts_engine import synthesize, VOICE_OPTIONS
from wan2gp_client import generate_clip
from lipsync import lipsync_clip
from stitcher import stitch_clips, save_to_drive

WORKDIR = "/content/pika_workdir"


def run_pipeline(character_image, story_text, voice_label, max_scenes, resolution, progress=gr.Progress()):
    if not character_image:
        raise gr.Error("Please upload a character reference image.")
    if not story_text or not story_text.strip():
        raise gr.Error("Please enter your story.")

    run_id = str(int(time.time()))
    run_dir = os.path.join(WORKDIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    scenes = split_story(story_text, max_scenes=int(max_scenes))
    if not scenes:
        raise gr.Error("Could not split the story into scenes — try adding more detail.")

    final_clip_paths = []
    total = len(scenes)

    for scene in scenes:
        progress((scene.index) / total, desc=f"Scene {scene.index + 1}/{total}: generating video")
        raw_clip = os.path.join(run_dir, f"scene_{scene.index:03d}_raw.mp4")
        generate_clip(
            prompt=scene.video_prompt,
            reference_image_path=character_image,
            out_path=raw_clip,
            resolution=resolution,
        )

        progress((scene.index + 0.4) / total, desc=f"Scene {scene.index + 1}/{total}: generating voice")
        audio_path = os.path.join(run_dir, f"scene_{scene.index:03d}_audio.mp3")
        synthesize(scene.narration, voice_label, audio_path)

        progress((scene.index + 0.7) / total, desc=f"Scene {scene.index + 1}/{total}: lip-sync")
        synced_clip = os.path.join(run_dir, f"scene_{scene.index:03d}_synced.mp4")
        result_path = lipsync_clip(raw_clip, audio_path, synced_clip)
        final_clip_paths.append(result_path)

    progress(0.95, desc="Stitching final video")
    final_path = os.path.join(run_dir, "final_video.mp4")
    stitch_clips(final_clip_paths, final_path)

    drive_path = None
    try:
        drive_path = save_to_drive(final_path)
    except Exception as e:
        print(f"[drive] could not save to Drive: {e}")

    status = f"Done — {total} scenes stitched."
    if drive_path:
        status += f" Saved to Drive: {drive_path}"
    else:
        status += " (Drive save skipped/failed — mount Drive in the notebook first.)"

    return final_path, status


CUSTOM_CSS = """
:root {
    --pika-bg: #ffffff;
    --pika-surface: #fafafa;
    --pika-border: #ececec;
    --pika-accent: #7c5cff;
    --pika-text: #1a1a1a;
}
.gradio-container {
    background: var(--pika-bg) !important;
    max-width: 480px !important;
    margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
#pika-title {
    text-align: center;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--pika-text);
    margin-bottom: 0;
}
#pika-subtitle {
    text-align: center;
    color: #8a8a8a;
    font-size: 0.85rem;
    margin-top: 0.2rem;
    margin-bottom: 1rem;
}
.gr-button-primary {
    background: var(--pika-accent) !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
}
.gr-box, .gr-input, .gr-textarea {
    border-radius: 14px !important;
    border: 1px solid var(--pika-border) !important;
    background: var(--pika-surface) !important;
}
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Soft(primary_hue="violet")) as demo:
        gr.HTML('<div id="pika-title">Pika-style Video Generator</div>'
                '<div id="pika-subtitle">Character + story \u2192 video, on your phone</div>')

        character_image = gr.Image(label="Character reference photo", type="filepath")
        story_text = gr.Textbox(label="Your story", lines=6, placeholder="Write your story here...")

        with gr.Row():
            voice = gr.Dropdown(label="Voice", choices=list(VOICE_OPTIONS.keys()),
                                 value=list(VOICE_OPTIONS.keys())[0])
            resolution = gr.Dropdown(label="Resolution", choices=["480p"], value="480p")

        max_scenes = gr.Slider(label="Number of scenes (start low on free Colab)",
                                minimum=2, maximum=60, value=8, step=1)

        generate_btn = gr.Button("Generate video", variant="primary")

        output_video = gr.Video(label="Result")
        status_box = gr.Textbox(label="Status", interactive=False)

        generate_btn.click(
            fn=run_pipeline,
            inputs=[character_image, story_text, voice, max_scenes, resolution],
            outputs=[output_video, status_box],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.queue().launch(share=True)
