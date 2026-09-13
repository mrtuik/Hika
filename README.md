# Pika-style Phone Video Generator (Wan2GP + Colab)

Phone-only, character + story to a single Wan2GP video clip. Attach a
character reference photo, describe the scene, tap send in a custom
ChatGPT-style UI, and get a video clip back.

Built on top of [Square-Zero-Labs/Wan2GP-on-Colab](https://github.com/Square-Zero-Labs/Wan2GP-on-Colab),
which sets up [Wan2GP](https://github.com/deepbeepmeep/Wan2GP) on a free Colab GPU.

**Scope, precisely:** one story + one character photo -> one generated
video clip. No voice, no lip-sync, no multi-scene story splitting, no
stitching into a longer video. Just Wan2GP's generation, behind a custom
phone-friendly chat UI.

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

## What this actually is (read before you run it)

This is a **first working version**, not a finished product. Please read
these limits honestly before you judge it:

- **Free Colab GPU = 15GB T4 VRAM.** Only `Wan 2.2 TextImage2Video FastWan`
  at 480p fits reliably. **Measured speed: ~8 minutes per 5-second clip.**
  That's the wait after you tap send — there is no way around it on a free
  GPU short of Colab Pro.
- **Character consistency is not guaranteed.** Wan2GP's Image2Video mode
  uses your reference photo as the *starting frame*, which keeps the look
  reasonably close but is not a trained identity/LoRA lock.
- Everything used here is **free**: Wan2GP is open-source, and the only
  other dependency is Gradio itself. No paid API, no voice, no lip-sync,
  no story-splitting pipeline — deliberately kept out of scope.

## Repo layout

```
pika_colab.ipynb          <- run this in Colab, top to bottom
pika_kaggle.ipynb          <- same thing, adapted for Kaggle notebooks
src/
  wan2gp_client.py          <- talks to Wan2GP's own Gradio server
  orchestrator_ui.py         <- your custom chat-style phone UI
requirements.txt
```

## How the pieces fit together

1. The notebook starts Wan2GP's own Gradio app in the background on
   `127.0.0.1:7860` (headless, no public link needed for it).
2. `wan2gp_client.py` connects to that local server with `gradio_client`
   and calls its generation function — so we never touch Wan2GP's
   internals directly, which keeps this working across Wan2GP updates.
3. `orchestrator_ui.py` is the chat-style app you actually use on your
   phone. It gets its own public link (via Gradio `share=True`). Attach a
   character photo, type a scene description, tap send — you get one
   generated video clip back in a card with a live timer while it works.

## One-time setup step you must do yourself

Wan2GP's Gradio app exposes its generate function as an API endpoint, but
the exact endpoint name can change between versions. After the notebook
launches Wan2GP, run the "inspect API" cell right after it — it prints the
available endpoint names. Paste the correct one into `WAN2GP_API_NAME` at
the top of `src/wan2gp_client.py` (a sensible default is already filled
in, but confirm it matches what you see).

## Running it

1. Open the notebook in Colab (GPU runtime, T4).
2. Run cells top to bottom.
3. The last cell prints a public link — open it on your phone.
4. Attach a character reference photo, type your scene, pick a model
   quality from the dropdown, tap send.
5. Wait (~8 min on free T4) — the card's timer shows it's still working.
   The video appears in the same card when it's done.
