# Pika-style Phone Video Generator (Wan2GP + Colab)

Phone-only, story-to-video generator: character reference + story text →
scene split → AI video clips (Wan2GP) → AI voice (edge-tts) → lip-sync
(Wav2Lip) → stitched final MP4 → saved to Google Drive.

Built on top of [Square-Zero-Labs/Wan2GP-on-Colab](https://github.com/Square-Zero-Labs/Wan2GP-on-Colab),
which sets up [Wan2GP](https://github.com/deepbeepmeep/Wan2GP) on a free Colab GPU.

## Open in Colab

After you push this repo to your own GitHub account, use this badge at the
top of your own README:

```
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mrtuik/Hika/blob/main/pika_colab.ipynb)
```

Or just open it directly with:
```
https://colab.research.google.com/github/mrtuik/Hika/blob/main/pika_colab.ipynb
```

## Colab vs Kaggle — which notebook to use

Both `pika_colab.ipynb` and `pika_kaggle.ipynb` do the same thing. Pick
based on what matters more to you:

| | `pika_colab.ipynb` | `pika_kaggle.ipynb` |
|---|---|---|
| Needs browser tab open to keep running? | Yes | **No** — use "Save & Run All (Commit)"; it keeps running in the background even with the tab closed |
| Session length | ~3-4 hrs before idle disconnect | ~9-12 hrs per run |
| Weekly GPU quota | Not fixed, but limited/variable | 30 GPU-hours/week (hard cap) |
| Persistent storage | Google Drive (optional, in Cell 2) | Kaggle's own Output/working folder |
| Opening from GitHub | One-click badge/link (above) | Kaggle > New Notebook > File > Import Notebook > GitHub tab > paste `mrtuik/Hika`, pick `pika_kaggle.ipynb` |

Neither one is a real 24/7 hosted service — that would need a paid GPU
(e.g. RunPod, billed per second) since no free tier allows an always-on
GPU process. Kaggle just needs far less babysitting than Colab for a
single long run.

### Using the Kaggle version
1. On kaggle.com: **Create > New Notebook**, then **File > Import Notebook
   > GitHub**, paste `mrtuik/Hika`, select `pika_kaggle.ipynb`.
2. Right sidebar: **Accelerator > GPU**, **Internet > On**.
3. Click **Save & Run All (Commit)** — do not just run cells interactively.
4. Once it's running, you can close the browser/lock your phone. Come back
   later, open the notebook's **Viewer/Logs**, and find the printed
   `https://xxxx.gradio.live` link — open that on your phone.
5. Final video appears in the notebook's **Output** tab after the run
   finishes or you check in on it.


## What this actually is (read before you run it)

This is a **first working version**, not a finished product. Please read
these limits honestly before you judge it:

- **Free Colab GPU = 15GB T4 VRAM.** Only `Wan 2.2 TextImage2Video FastWan`
  at 480p fits reliably. **Measured speed: ~8 minutes per 5-second clip.**
  That means a true 5-minute video (~60 clips) would take **~8 hours of
  generation alone** — not realistic in one free Colab session (these
  disconnect long before that). Start with `max_scenes = 5-10` (25-50
  seconds of final video) and scale up only if you have Colab Pro or plan
  to resume the work across multiple sessions using Drive persistence.
- **Character consistency is the hardest unsolved part.** Wan2GP's
  Image2Video mode uses your reference image as the *starting frame* of
  each clip, which keeps the character reasonably consistent scene-to-scene
  but is not a trained identity/LoRA lock. Expect drift over many scenes.
- **Lip-sync (Wav2Lip)** works best on a clear, front-facing face and only
  syncs mouth movement to the audio — it does not generate acting/emotion.
- **Story splitting** here is a simple rule-based sentence/length splitter,
  not an LLM. It's free and works offline, but a paid LLM call (optional)
  will produce better scene descriptions if you want to add one later.
- Everything used here is **free**: Wan2GP (open-source), edge-tts (free,
  no API key), Wav2Lip (open-source), ffmpeg. No paid API is required.

## Repo layout

```
pika_colab.ipynb        <- run this in Colab, top to bottom
src/
  story_splitter.py      <- splits story text into scenes
  tts_engine.py           <- free text-to-speech (edge-tts)
  lipsync.py              <- Wav2Lip wrapper
  stitcher.py             <- ffmpeg concat + mux to final MP4
  wan2gp_client.py         <- talks to Wan2GP's own Gradio server
  orchestrator_ui.py       <- your custom white/premium phone UI
requirements.txt
```

## How the pieces fit together

1. The notebook starts Wan2GP's own Gradio app in the background on
   `127.0.0.1:7860` (headless, no public link needed for it).
2. `wan2gp_client.py` connects to that local server with `gradio_client`
   and calls its generation function per scene — so we never touch
   Wan2GP's internals directly, which keeps this working across Wan2GP
   updates.
3. Our own `orchestrator_ui.py` app is the one you actually use on your
   phone. It gets its own public Colab link (via Gradio `share=True`).
4. For each scene: generate video clip -> generate voice line -> lip-sync
   -> collect. At the end, `stitcher.py` joins every scene into one MP4
   and copies it to Google Drive.

## One-time setup step you must do yourself

Wan2GP's Gradio app exposes its generate function as an API endpoint, but
the exact endpoint name can change between versions. After the notebook
launches Wan2GP in Cell 5, run the small "inspect API" cell right after it
— it prints the available endpoint names. Paste the correct one into
`WAN2GP_API_NAME` at the top of `src/wan2gp_client.py` (a sensible default
is already filled in, but confirm it matches what you see).

## Running it

1. Open the notebook in Colab (GPU runtime).
2. Run cells top to bottom.
3. The last cell prints a public link — open it on your phone.
4. Upload a character reference photo, paste your story, pick a voice,
   set `max_scenes`, tap Generate.
5. When done, the video plays in-app and is also saved to
   `MyDrive/PikaVideoGenerator/output/`.
