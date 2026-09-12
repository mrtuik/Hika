"""
Talks to Wan2GP's own Gradio app as a black box over its local API, instead
of importing Wan2GP's internals directly. This keeps us decoupled from
Wan2GP's internal code changing between versions.

SETUP REQUIRED (one time):
  1. The notebook launches Wan2GP headless on WAN2GP_URL (Cell 5).
  2. Run the "inspect API" cell right after it. It prints something like:

        api_name: /generate_video
        parameters: [prompt, image, resolution, ...]

  3. Confirm WAN2GP_API_NAME below matches what you saw. If Wan2GP's
     Gradio UI structure changes upstream, this is the only place you
     should need to update.
"""

import os
import shutil

from gradio_client import Client, handle_file

WAN2GP_URL = "http://127.0.0.1:7860"
WAN2GP_API_NAME = "/generate_video"  # confirm via the "inspect API" cell

_client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(WAN2GP_URL)
    return _client


def inspect_api():
    """Run this once from a notebook cell to print the real endpoint names
    and parameter order for your installed Wan2GP version."""
    get_client().view_api()


def generate_clip(
    prompt: str,
    reference_image_path: str,
    out_path: str,
    resolution: str = "480p",
    model: str = "Wan 2.2 TextImage2Video 5B FastWan",
) -> str:
    """
    Args:
        prompt: text prompt for this scene.
        reference_image_path: character reference image (keeps the
            character's look as the starting frame for this clip).
        out_path: where to copy the resulting clip.
        resolution: keep at 480p on a free Colab T4 (see README).
        model: keep at the FastWan 5B model on a free Colab T4.

    Returns:
        out_path.

    NOTE: the positional args passed to `client.predict` below are a
    reasonable guess based on Wan2GP's typical Image2Video inputs
    (prompt, image, resolution, model). Confirm the actual order/names
    with `inspect_api()` and adjust this call if they differ — Gradio's
    `predict` also accepts keyword args matching the labels shown by
    `view_api()`, which is often more robust than positional order.
    """
    client = get_client()
    result = client.predict(
        prompt,
        handle_file(reference_image_path),
        resolution,
        model,
        api_name=WAN2GP_API_NAME,
    )

    # Wan2GP typically returns a filepath (or dict containing one) for the
    # generated video. Handle both shapes defensively.
    result_path = result
    if isinstance(result, dict):
        result_path = result.get("video") or result.get("path") or result.get("name")
    if isinstance(result_path, (list, tuple)):
        result_path = result_path[0]

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    shutil.copy(result_path, out_path)
    return out_path
