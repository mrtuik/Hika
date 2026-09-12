"""
Thin wrapper around Wav2Lip's inference.py.

The notebook clones Wav2Lip into WAV2LIP_DIR and downloads the pretrained
checkpoint there (see pika_colab.ipynb, Cell 6). This module just shells
out to Wav2Lip's own inference script per scene — this keeps us decoupled
from Wav2Lip's internals.

Notes:
  - Wav2Lip needs a clearly visible, mostly front-facing face in the video
    clip. If Wan2GP's clip doesn't show the character's face in frame for
    a given scene, lip-sync will fail or look wrong for that scene — the
    pipeline falls back to using the un-synced clip in that case rather
    than failing the whole run.
  - This step is itself GPU/CPU-time heavy; expect it to roughly add as
    much time again as the video generation step per scene.
"""

import os
import subprocess

WAV2LIP_DIR = "/content/Wav2Lip"
CHECKPOINT_PATH = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")


def lipsync_clip(video_path: str, audio_path: str, out_path: str) -> str:
    """
    Args:
        video_path: silent video clip from Wan2GP for one scene.
        audio_path: narration audio for the same scene.
        out_path: where to write the lip-synced result.

    Returns:
        out_path if lip-sync succeeded, otherwise the original video_path
        (so the pipeline can continue instead of crashing on one scene).
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    cmd = [
        "python", os.path.join(WAV2LIP_DIR, "inference.py"),
        "--checkpoint_path", CHECKPOINT_PATH,
        "--face", video_path,
        "--audio", audio_path,
        "--outfile", out_path,
        "--pads", "0", "10", "0", "0",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        if os.path.exists(out_path):
            return out_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[lipsync] failed for {video_path}, falling back to original clip: {e}")

    return video_path
