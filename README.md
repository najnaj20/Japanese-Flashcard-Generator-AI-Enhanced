# 🇯🇵 Japanese Flashcard Generator — AI-Enhanced

<div align="center">

**Turn Japanese videos & audio into Anki flashcards — automatically.**  
**Ubah video & audio Jepang jadi flashcard Anki — secara otomatis.**

[Features](#-features--fitur) · [How It Works](#-how-it-works--cara-kerja) · [Setup](#-setup--instalasi) · [Deploy on Streamlit Cloud](#-deploy-on-streamlit-cloud)

</div>

---

## ✨ Features / Fitur

### 🇬🇧 English

- **🎥 YouTube Processing** — paste any YouTube URL (Japanese podcasts, dramas, news, anime clips) and the app downloads and transcribes the audio.
- **🎵 Audio Upload** — or upload your own audio files (mp3, wav, m4a, ogg).
- **🧠 Speech-to-Text with Whisper** — transcription powered by `faster-whisper` (CTranslate2 backend, int8 quantized — fast even on CPU, no PyTorch needed).
- **🔍 AI Vocabulary Extraction** — GPT-3.5 Turbo (or any OpenAI-compatible model) extracts useful Japanese vocabulary with kanji readings, JLPT level estimates, and natural example sentences.
- **🌐 Smart Translation** — Japanese → English/Indonesian via GPT, with a **free Google Translate fallback** when no API key is set.
- **🎴 Anki Export** — download ready-to-import `.apkg` flashcard decks with audio pronunciation (gTTS) on each card.

### 🇮🇩 Bahasa Indonesia

- **🎥 Proses YouTube** — tempel URL YouTube apa pun (podcast, drama, berita, klip anime Jepang); audio otomatis diunduh dan ditranskripsi.
- **🎵 Upload Audio** — atau unggah file audio sendiri (mp3, wav, m4a, ogg).
- **🧠 Speech-to-Text dengan Whisper** — transkripsi memakai `faster-whisper` (backend CTranslate2, int8 — cepat bahkan di CPU, tanpa PyTorch).
- **🔍 Ekstraksi Kosakata AI** — GPT-3.5 Turbo (atau model kompatibel OpenAI lain) mengekstrak kosakata Jepang lengkap dengan bacaan kanji, estimasi level JLPT, dan contoh kalimat natural.
- **🌐 Terjemahan Cerdas** — Jepang → Inggris/Indonesia via GPT, dengan **fallback Google Translate gratis** jika tidak ada API key.
- **🎴 Ekspor Anki** — unduh deck flashcard `.apkg` yang siap di-import, lengkap dengan audio pelafalan (gTTS) di setiap kartu.

---

## 🔄 How It Works / Cara Kerja

```
YouTube URL / Audio File
        │
        ▼
  faster-whisper  ──►  Transcription / Transkripsi
        │
        ▼
  GPT vocabulary extraction  ──►  Word list + readings + JLPT level
  (fallback: Google Translate / deep-translator)
        │
        ▼
  genanki + gTTS  ──►  Download .apkg  ──►  Import to Anki 🎉
```

1. Paste a YouTube URL **or** upload an audio file / Tempel URL YouTube **atau** unggah file audio
2. Click **Process** and wait for the transcription / Klik **Process** dan tunggu hasil transkripsi
3. Click **🔍 Extract Vocabulary** / Klik **🔍 Extract Vocabulary**
4. Review the words, then **🎴 Create AI-Enhanced Flashcards** / Periksa kosakata, lalu **🎴 Create AI-Enhanced Flashcards**
5. Download the `.apkg` and import it into Anki / Unduh `.apkg` lalu import ke Anki

---

## 🚀 Setup / Instalasi

### 🇬🇧 English

```bash
git clone https://github.com/najnaj20/Japanese-Flashcard-Generator-AI-Enhanced.git
cd Japanese-Flashcard-Generator-AI-Enhanced

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

streamlit run main.py
```

### 🇮🇩 Bahasa Indonesia

```bash
git clone https://github.com/najnaj20/Japanese-Flashcard-Generator-AI-Enhanced.git
cd Japanese-Flashcard-Generator-AI-Enhanced

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt   # tidak perlu torch/PyTorch 🎉

streamlit run main.py             # buka http://localhost:8501
```

> **Requires / Butuh:** Python 3.10+ (tested on 3.11)

---

## 🔑 API Key (Optional / Opsional)

The app **runs without an API key** — translation falls back to free Google Translate. To unlock the full AI vocabulary enhancement / App tetap jalan **tanpa API key** — terjemahan memakai Google Translate gratis. Untuk fitur AI penuh:

```bash
export OPENAI_API_KEY="***"
# optional — custom compatible endpoint (e.g. B.AI, Together, etc.)
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

On Streamlit Cloud, add these in **Settings → Secrets** as:

```toml
OPENAI_API_KEY="***"
```

---

## ☁️ Deploy on Streamlit Cloud

1. Push this repo to GitHub (done ✅ / sudah ✅)
2. Go to <https://share.streamlit.io> → sign in with GitHub
3. **New app** → pick this repo, branch `main`, **Main script: `main.py`**
4. Deploy. First Whisper model download takes ~1 minute on boot.
5. (Optional) Add `OPENAI_API_KEY` under **Settings → Secrets**

> ⚠️ **Note:** do not commit a local `.venv/` folder — Streamlit Cloud builds break when one is present. It is already covered by `.gitignore` here.

---

## 🗂️ Project Structure / Struktur Proyek

```
├── main.py                  # Streamlit entry point / titik masuk
├── app/
│   ├── config/              # settings & logging
│   └── utils/
│       ├── audio.py         # yt-dlp download + faster-whisper transcription
│       ├── ai_helper.py     # OpenAI-compatible vocabulary extraction
│       ├── translator.py    # GPT translation + Google Translate fallback
│       ├── vocabulary.py    # Japanese tokenizing (fugashi/unidic) & cleaning
│       └── flashcard.py     # genanki .apkg generation + gTTS audio
├── requirements.txt         # lean deps — no torch 🎉
├── runtime.txt              # Python version for Streamlit Cloud
└── .streamlit/config.toml   # theme & server config
```

---

## 🛠️ Tech Stack

`Streamlit` · `faster-whisper` · `OpenAI API (GPT-3.5)` · `deep-translator` · `yt-dlp` · `genanki` · `gTTS` · `fugashi/unidic-lite` · `pandas`

---

## 📄 License

MIT — free to use, modify, and learn from. / Bebas digunakan, dimodifikasi, dan dipelajari.

---

<div align="center">

Built with ☕, 🍙 and Anki-colored procrastination.  
*Made by [najnaj20](https://github.com/najnaj20)*

</div>
