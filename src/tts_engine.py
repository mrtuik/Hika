"""
Free text-to-speech using edge-tts (Microsoft Edge's online voices, no API
key, no cost). Produces one mp3/wav per scene.

If edge-tts's servers are ever unreachable for you, swap this module for
Coqui TTS (fully offline) without touching any other file — this module's
only public contract is `synthesize(text, voice, out_path)`.
"""

import asyncio
import os

import edge_tts

# A handful of good default voices. Full list: `edge-tts --list-voices`
VOICE_OPTIONS = {
    "Bengali (Female)": "bn-BD-NabanitaNeural",
    "Bengali (Male)": "bn-BD-PradeepNeural",
    "English (Female)": "en-US-AriaNeural",
    "English (Male)": "en-US-GuyNeural",
}


async def _synthesize_async(text: str, voice: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def synthesize(text: str, voice_label: str, out_path: str) -> str:
    """
    Args:
        text: narration text for one scene.
        voice_label: a key from VOICE_OPTIONS (shown in the UI dropdown).
        out_path: where to write the audio file (.mp3).

    Returns:
        out_path, for convenience chaining.
    """
    voice = VOICE_OPTIONS.get(voice_label, "en-US-AriaNeural")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    asyncio.run(_synthesize_async(text, voice, out_path))
    return out_path
