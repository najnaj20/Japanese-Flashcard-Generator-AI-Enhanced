# 🇯🇵 Japanese Flashcard Generator — AI-Enhanced

> 📖 [English](README.md) · [Bahasa Indonesia](README.id.md)

Streamlit app that turns **Japanese videos (YouTube) or audio files** into
**Anki-ready flashcard decks**: Whisper transcription → AI vocabulary
extraction (kanji readings, JLPT level, example sentences) → `.apkg` export
with TTS pronunciation audio. Built as a portfolio project: real pipeline,
zero-GPU dependency (no PyTorch — `faster-whisper` int8 on CPU), runs even
without an API key (free Google Translate fallback).

**Pipeline:** YouTube/audio → faster-whisper → GPT vocabulary → genanki `.apkg` · **Stack:** Streamlit + CTranslate2 + OpenAI-compatible API

## What's inside

```
Japanese-Flashcard-Generator-AI-Enhanced/
├── main.py                  # Streamlit entry point (UI + flow orchestration)
├── app/
│   ├── config/              # settings & logging
│   └── utils/
│       ├── audio.py         # yt-dlp download + faster-whisper transcription (int8, CPU)
│       ├── ai_helper.py     # OpenAI-compatible vocabulary extraction
│       ├── translator.py    # GPT translation + free Google Translate fallback
│       ├── vocabulary.py    # Japanese tokenizing (fugashi/unidic) & cleaning
│       └── flashcard.py     # genanki .apkg generation + gTTS audio per card
├── requirements.txt         # lean deps — no torch 🎉
├── runtime.txt              # Python version for Streamlit Cloud
├── .streamlit/config.toml   # dark theme & server config
└── Dockerfile               # optional container run
```

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # no PyTorch needed

streamlit run main.py
# open http://localhost:8501
```

### Workflow

1. Paste a **YouTube URL** or upload an **audio file** (mp3/wav/m4a/ogg)
2. Click **Process** → wait for the Whisper transcription
3. Click **🔍 Extract Vocabulary** → review words, readings, JLPT levels
4. Click **🎴 Create AI-Enhanced Flashcards** → download the `.apkg`
5. Import into **Anki** and start studying 🎉

## 🔑 API key (optional)

The app **runs without any key** — translation falls back to free Google
Translate. To unlock the full GPT vocabulary enhancement, set:

```bash
export OPENAI_API_KEY="***"
export OPENAI_BASE_URL="https://api…/v1"   # optional, any compatible endpoint
```

On Streamlit Cloud: **Settings → Secrets** → `OPENAI_API_KEY="***"`.

## ☁️ Deploy on Streamlit Cloud

1. Go to <https://share.streamlit.io> → sign in with GitHub
2. **New app** → this repo, branch `main`, **Main script: `main.py`**
3. Deploy — first boot downloads the Whisper base model (~1 min)

> ⚠️ Never commit a local `.venv/` folder — Streamlit Cloud builds break when
> one is present (already covered by `.gitignore`).

## Honest limitations

- **Whisper `base` model** is used for CPU friendliness; accuracy drops on
  fast speech, names, and slang. Longer videos (>10 min) take a while on free-tier hardware.
- **Vocabulary extraction quality** depends on the LLM available; without an
  API key the app falls back to heuristic tokenizing + Google Translate, which
  misses nuance (contextual readings, colloquial meanings).
- **YouTube downloading** depends on `yt-dlp` keeping up with site changes —
  if a video fails, uploading the audio file directly is the reliable path.
- This is a **portfolio/learning tool**, not a substitute for a textbook or
  SRS coaching; always review extracted words before importing decks.

## Data sources & licenses

- **OpenAI / compatible LLM APIs** for enhancement (your own key, optional).
- **Google Translate** via `deep-translator` as the free fallback.
- **gTTS** for card pronunciation audio (Google Translate TTS endpoint).
- Code licensed **MIT** — free to use, modify, and learn from.
