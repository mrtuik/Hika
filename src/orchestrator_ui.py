"""
Custom chat-style UI (ChatGPT-like layout):
  - left drawer: configuration (voice, scene count, resolution/model)
  - main column: scrolling message history
  - bottom input bar: attach (character photo) + model dropdown + text + send
  - on send: a minimal card appears showing a live timer while it generates

This is a separate Gradio app from Wan2GP's own UI, launched with its own
public share link from the notebook's final cell.
"""

import base64
import concurrent.futures
import html
import os
import time

import gradio as gr

from story_splitter import split_story
from tts_engine import synthesize, VOICE_OPTIONS
from wan2gp_client import generate_clip
from lipsync import lipsync_clip
from stitcher import stitch_clips, save_to_drive

WORKDIR = "/content/pika_workdir"

MODEL_OPTIONS = {
    "FastWan 5B \u2014 480p (recommended, fits free T4)": "480p",
    "FastWan 5B \u2014 720p (needs more VRAM, may fail on free T4)": "720p",
}


def _img_to_data_uri(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lstrip(".").lower() or "jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{ext};base64,{b64}"


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def user_bubble(story_text: str, character_image: str) -> str:
    thumb = _img_to_data_uri(character_image)
    thumb_html = f'<img class="char-thumb" src="{thumb}" />' if thumb else ""
    return (
        '<div class="msg user">'
        '<div class="bubble">'
        f'{thumb_html}'
        f'<p>{html.escape(story_text)}</p>'
        '</div></div>'
    )


def progress_card(scene_no: int, total: int, step_label: str, elapsed: float) -> str:
    pct = 0 if total == 0 else int(100 * (scene_no - 1) / total)
    return (
        '<div class="msg assistant"><div class="card">'
        '<div class="card-header">'
        f'<span class="scene-label">Scene {scene_no}/{total}</span>'
        f'<span class="timer">{_fmt_time(elapsed)}</span>'
        '</div>'
        f'<div class="card-desc">{html.escape(step_label)}</div>'
        '<div class="progress-track">'
        f'<div class="progress-fill" style="width:{pct}%"></div>'
        '</div></div></div>'
    )


def result_card(video_path: str, status: str) -> str:
    video_tag = ""
    if video_path and os.path.exists(video_path):
        with open(video_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        video_tag = (
            f'<video class="result-video" controls src="data:video/mp4;base64,{b64}"></video>'
        )
    return (
        '<div class="msg assistant"><div class="card">'
        '<div class="card-header"><span class="scene-label">Done</span></div>'
        f'{video_tag}'
        f'<div class="card-desc">{html.escape(status)}</div>'
        '</div></div>'
    )


def error_card(message: str) -> str:
    return (
        '<div class="msg assistant"><div class="card card-error">'
        f'<div class="card-desc">{html.escape(message)}</div>'
        '</div></div>'
    )


def run_pipeline(chat_html, character_image, story_text, model_label, voice_label, max_scenes):
    if not character_image:
        chat_html += error_card("Please attach a character reference photo first.")
        yield chat_html, ""
        return
    if not story_text or not story_text.strip():
        chat_html += error_card("Please type your story first.")
        yield chat_html, ""
        return

    resolution = MODEL_OPTIONS.get(model_label, "480p")
    chat_html += user_bubble(story_text, character_image)
    yield chat_html, ""

    run_id = str(int(time.time()))
    run_dir = os.path.join(WORKDIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    scenes = split_story(story_text, max_scenes=int(max_scenes))
    if not scenes:
        chat_html += error_card("Couldn't split that story into scenes \u2014 try adding a bit more detail.")
        yield chat_html, ""
        return

    total = len(scenes)
    final_clip_paths = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    base_html = chat_html

    def run_with_timer(label, fn, *args):
        nonlocal chat_html
        future = executor.submit(fn, *args)
        step_start = time.time()
        while not future.done():
            elapsed = time.time() - step_start
            chat_html = base_html + progress_card(scene.index + 1, total, label, elapsed)
            yield chat_html, ""
            time.sleep(1)
        chat_html = base_html + progress_card(scene.index + 1, total, label, time.time() - step_start)
        yield chat_html, ""
        return future.result()

    for scene in scenes:
        raw_clip = os.path.join(run_dir, f"scene_{scene.index:03d}_raw.mp4")
        gen = run_with_timer(
            "Generating video clip...", generate_clip,
            scene.video_prompt, character_image, raw_clip, resolution,
        )
        result = None
        try:
            while True:
                out = next(gen)
                yield out
        except StopIteration as stop:
            result = stop.value

        audio_path = os.path.join(run_dir, f"scene_{scene.index:03d}_audio.mp3")
        chat_html = base_html + progress_card(scene.index + 1, total, "Generating voice line...", 0)
        yield chat_html, ""
        synthesize(scene.narration, voice_label, audio_path)

        synced_clip = os.path.join(run_dir, f"scene_{scene.index:03d}_synced.mp4")
        gen2 = run_with_timer(
            "Lip-syncing...", lipsync_clip,
            raw_clip, audio_path, synced_clip,
        )
        try:
            while True:
                out = next(gen2)
                yield out
        except StopIteration as stop:
            result_path = stop.value

        final_clip_paths.append(result_path)
        base_html = chat_html

    chat_html = base_html + progress_card(total, total, "Stitching final video...", 0)
    yield chat_html, ""
    final_path = os.path.join(run_dir, "final_video.mp4")
    stitch_clips(final_clip_paths, final_path)

    drive_path = None
    try:
        drive_path = save_to_drive(final_path)
    except Exception as e:
        print(f"[drive] could not save to Drive: {e}")

    status = f"{total} scenes stitched."
    status += f" Saved to Drive: {drive_path}" if drive_path else " (Drive save skipped \u2014 mount Drive in the notebook.)"

    chat_html = base_html + result_card(final_path, status)
    yield chat_html, ""


FONT_IMPORT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"

CUSTOM_CSS = f"""
@import url('{FONT_IMPORT}');

:root {{
    --bg: #ffffff;
    --border: #e8e8e8;
    --text: #111111;
    --text-secondary: #8a8a8a;
    --surface: #fafafa;
}}
* {{ font-family: 'Inter', -apple-system, sans-serif !important; }}
.gradio-container {{
    background: var(--bg) !important;
    max-width: 480px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}}
#app-shell {{ display: flex; flex-direction: column; height: 100vh; }}

#top-bar {{
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; border-bottom: 1px solid var(--border);
}}
#top-bar button {{
    background: none !important; border: none !important; box-shadow: none !important;
    font-size: 1.1rem; padding: 4px 8px !important; min-width: auto !important;
    color: var(--text) !important;
}}
#top-title {{ font-weight: 600; font-size: 0.95rem; color: var(--text); }}

#chat-scroll {{
    flex: 1; overflow-y: auto; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
}}
.msg {{ display: flex; }}
.msg.user {{ justify-content: flex-end; }}
.msg.assistant {{ justify-content: flex-start; }}
.bubble {{
    background: #111111; color: #ffffff;
    border-radius: 10px; padding: 8px 12px; max-width: 82%;
}}
.bubble p {{ margin: 6px 0 0 0; font-size: 0.9rem; line-height: 1.4; }}
.char-thumb {{ width: 100%; max-width: 160px; border-radius: 8px; display: block; }}

.card {{
    background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
    padding: 10px 12px; max-width: 82%; box-shadow: none;
}}
.card-error {{ border-color: #c9c9c9; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; }}
.scene-label {{ font-size: 0.8rem; font-weight: 600; color: var(--text); }}
.timer {{ font-size: 0.8rem; color: var(--text-secondary); font-variant-numeric: tabular-nums; }}
.card-desc {{ font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px; }}
.progress-track {{ height: 3px; background: var(--border); border-radius: 2px; margin-top: 8px; }}
.progress-fill {{ height: 3px; background: var(--text); border-radius: 2px; }}
.result-video {{ width: 100%; border-radius: 8px; margin-top: 6px; }}

#drawer {{
    border-right: 1px solid var(--border); padding: 14px 12px; background: var(--surface);
}}
#drawer h4 {{ font-size: 0.8rem; color: var(--text-secondary); margin: 10px 0 4px 0; font-weight: 600; }}

#input-bar {{
    border-top: 1px solid var(--border); padding: 8px 10px;
    display: flex; align-items: flex-end; gap: 6px; background: var(--bg);
}}
#input-bar .attach-btn button {{
    border-radius: 999px !important; width: 36px !important; height: 36px !important;
    min-width: 36px !important; padding: 0 !important; border: 1px solid var(--border) !important;
    background: var(--bg) !important; color: var(--text) !important; box-shadow: none !important;
}}
#input-bar textarea {{
    border-radius: 18px !important; border: 1px solid var(--border) !important;
    padding: 8px 14px !important; font-size: 0.9rem !important; background: var(--surface) !important;
}}
#send-btn button {{
    border-radius: 999px !important; width: 36px !important; height: 36px !important;
    min-width: 36px !important; padding: 0 !important; background: #111111 !important;
    color: #ffffff !important; border: none !important; box-shadow: none !important;
}}
#model-dropdown {{ min-width: 0 !important; }}
#model-dropdown div {{ font-size: 0.78rem !important; }}
#char-preview img {{ border-radius: 8px !important; max-height: 60px !important; }}
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(css=CUSTOM_CSS, title="Pika-style Video Generator") as demo:
        with gr.Column(elem_id="app-shell"):
            with gr.Row(elem_id="top-bar"):
                menu_btn = gr.Button("\u2630", elem_id="menu-btn")
                gr.HTML('<div id="top-title">Video Generator</div>')

            with gr.Row(equal_height=False):
                with gr.Column(scale=0, min_width=210, visible=False) as drawer:
                    with gr.Column(elem_id="drawer"):
                        gr.HTML("<h4>Voice</h4>")
                        voice = gr.Dropdown(
                            choices=list(VOICE_OPTIONS.keys()),
                            value=list(VOICE_OPTIONS.keys())[0],
                            show_label=False, container=False,
                        )
                        gr.HTML("<h4>Number of scenes</h4>")
                        max_scenes = gr.Slider(
                            minimum=2, maximum=20, value=6, step=1, show_label=False, container=False,
                        )
                        gr.HTML(
                            '<div style="font-size:0.72rem;color:#8a8a8a;margin-top:6px;">'
                            '~8 min/scene on a free Colab T4</div>'
                        )

                with gr.Column(scale=1):
                    chat_display = gr.HTML('<div id="chat-scroll"></div>')

            character_image = gr.Image(type="filepath", visible=False, elem_id="char-preview")

            with gr.Row(elem_id="input-bar"):
                attach_btn = gr.UploadButton("+", file_types=["image"], elem_classes="attach-btn")
                model = gr.Dropdown(
                    choices=list(MODEL_OPTIONS.keys()), value=list(MODEL_OPTIONS.keys())[0],
                    show_label=False, container=False, elem_id="model-dropdown", scale=0, min_width=90,
                )
                story_text = gr.Textbox(
                    placeholder="Describe your story...", show_label=False, container=False,
                    lines=1, max_lines=4, scale=1,
                )
                send_btn = gr.Button("\u27a4", elem_id="send-btn")

        chat_state = gr.State("")

        def toggle_drawer(is_open):
            return gr.update(visible=not is_open), not is_open

        drawer_open = gr.State(False)
        menu_btn.click(toggle_drawer, inputs=[drawer_open], outputs=[drawer, drawer_open])

        def on_attach(file):
            return gr.update(value=file, visible=bool(file))

        attach_btn.upload(on_attach, inputs=[attach_btn], outputs=[character_image])

        def render(chat_html):
            return f'<div id="chat-scroll">{chat_html}</div>'

        def wrapped_pipeline(*args):
            for chat_html, cleared_text in run_pipeline(*args):
                yield render(chat_html), chat_html, cleared_text

        send_btn.click(
            fn=wrapped_pipeline,
            inputs=[chat_state, character_image, story_text, model, voice, max_scenes],
            outputs=[chat_display, chat_state, story_text],
        )
        story_text.submit(
            fn=wrapped_pipeline,
            inputs=[chat_state, character_image, story_text, model, voice, max_scenes],
            outputs=[chat_display, chat_state, story_text],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.queue().launch(share=True)
