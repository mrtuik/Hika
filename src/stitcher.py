"""
Joins per-scene lip-synced clips into a single final MP4 using ffmpeg's
concat demuxer, then (optionally) copies the result into Google Drive.
"""

import os
import shutil
import subprocess
from typing import List


def stitch_clips(clip_paths: List[str], out_path: str) -> str:
    if not clip_paths:
        raise ValueError("No clips to stitch.")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    list_file = out_path + ".concat_list.txt"

    with open(list_file, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.remove(list_file)
    return out_path


def save_to_drive(local_path: str, drive_folder: str = "/content/drive/MyDrive/PikaVideoGenerator/output") -> str:
    """Copies the final video into Google Drive. Requires that
    drive.mount('/content/drive') was already run in the notebook."""
    os.makedirs(drive_folder, exist_ok=True)
    dest = os.path.join(drive_folder, os.path.basename(local_path))
    shutil.copy(local_path, dest)
    return dest
