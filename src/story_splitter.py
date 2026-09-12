"""
Splits a free-text story into a list of short "scenes" that can each be
turned into one Wan2GP video clip + one TTS line.

This is intentionally simple and free (no LLM call). It:
  1. Splits the story into sentences.
  2. Greedily groups sentences into scenes under a max word budget.
  3. Caps the total number of scenes (so a free Colab GPU has a chance of
     finishing before the session times out).

If you later want better scene descriptions (camera angle, mood, etc.) you
can swap `split_story` for a call to any LLM API — the rest of the
pipeline only cares about getting back a list of Scene objects.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class Scene:
    index: int
    narration: str      # text to speak (TTS) for this scene
    video_prompt: str    # text prompt to feed Wan2GP for this scene


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u0964\u0965])\s+")


def _split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def split_story(
    story: str,
    max_scenes: int = 10,
    max_words_per_scene: int = 25,
) -> List[Scene]:
    """
    Args:
        story: full story/prompt text from the user.
        max_scenes: hard cap on number of scenes (protects free-GPU runtime).
        max_words_per_scene: rough word budget per scene before starting a
            new one.

    Returns:
        List[Scene], each with narration (for TTS) and video_prompt (for
        Wan2GP). video_prompt is currently the same text as narration —
        edit here if you want to prepend a style prefix (see STYLE_PREFIX).
    """
    sentences = _split_sentences(story)
    if not sentences:
        return []

    scenes: List[Scene] = []
    current: List[str] = []
    current_words = 0

    def flush():
        nonlocal current, current_words
        if current:
            narration = " ".join(current)
            scenes.append(
                Scene(
                    index=len(scenes),
                    narration=narration,
                    video_prompt=f"{STYLE_PREFIX}{narration}",
                )
            )
            current = []
            current_words = 0

    for sentence in sentences:
        word_count = len(sentence.split())
        if current_words + word_count > max_words_per_scene and current:
            flush()
            if len(scenes) >= max_scenes:
                break
        current.append(sentence)
        current_words += word_count

    if len(scenes) < max_scenes:
        flush()

    return scenes[:max_scenes]


# Prepended to every video prompt sent to Wan2GP. Edit this to steer the
# overall visual style (e.g. "cinematic, soft lighting, ") consistently
# across every scene.
STYLE_PREFIX = ""
