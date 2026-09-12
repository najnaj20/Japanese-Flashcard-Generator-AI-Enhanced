# 🇯🇵 Japanese Flashcard Generator — AI-Enhanced

> 📖 [English](README.md) · [Bahasa Indonesia](README.id.md)

Aplikasi Streamlit yang mengubah **video Jepang (YouTube) atau file audio**
menjadi **deck flashcard Anki**: transkripsi Whisper → ekstraksi kosakata oleh
AI (bacaan kanji, level JLPT, contoh kalimat) → ekspor `.apkg` lengkap dengan
audio pelafalan TTS. Dibangun sebagai proyek portofolio: pipeline nyata, tanpa
dependensi GPU (tanpa PyTorch — `faster-whisper` int8 di CPU), tetap jalan
meski tanpa API key (fallback Google Translate gratis).

**Pipeline:** YouTube/audio → faster-whisper → kosakata via GPT → `.apkg` genanki · **Stack:** Streamlit + CTranslate2 + API kompatibel OpenAI

## Isi proyek

```
Japanese-Flashcard-Generator-AI-Enhanced/
├── main.py                  # titik masuk Streamlit (UI + orkestrasi alur)
├── app/
│   ├── config/              # pengaturan & logging
│   └── utils/
│       ├── audio.py         # unduhan yt-dlp + transkripsi faster-whisper (int8, CPU)
│       ├── ai_helper.py     # ekstraksi kosakata via API kompatibel OpenAI
│       ├── translator.py    # terjemahan GPT + fallback Google Translate gratis
│       ├── vocabulary.py    # tokenisasi & pembersihan teks Jepang (fugashi/unidic)
│       └── flashcard.py     # pembuatan .apkg via genanki + audio gTTS per kartu
├── requirements.txt         # deps ramping — tanpa torch 🎉
├── runtime.txt              # versi Python untuk Streamlit Cloud
├── .streamlit/config.toml   # konfigurasi dark theme & server
└── Dockerfile               # opsional, jalankan via container
```

## Cara menjalankan

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # tidak perlu PyTorch

streamlit run main.py
# buka http://localhost:8501
```

### Alur pemakaian

1. Tempel **URL YouTube** atau unggah **file audio** (mp3/wav/m4a/ogg)
2. Klik **Process** → tunggu hasil transkripsi Whisper
3. Klik **🔍 Extract Vocabulary** → periksa kata, bacaan, dan level JLPT
4. Klik **🎴 Create AI-Enhanced Flashcards** → unduh file `.apkg`
5. Import ke **Anki** dan mulai belajar 🎉

## 🔑 API key (opsional)

Aplikasi **tetap jalan tanpa key** — terjemahan memakai fallback Google
Translate gratis. Untuk membuka fitur ekstraksi kosakata AI penuh, set:

```bash
export OPENAI_API_KEY="***"
export OPENAI_BASE_URL="https://api…/v1"   # opsional, endpoint kompatibel apa pun
```

Di Streamlit Cloud: **Settings → Secrets** → `OPENAI_API_KEY="***"`.

## ☁️ Deploy ke Streamlit Cloud

1. Buka <https://share.streamlit.io> → login dengan GitHub
2. **New app** → repo ini, branch `main`, **Main script: `main.py`**
3. Deploy — boot pertama mengunduh model Whisper base (~1 menit)

> ⚠️ Jangan pernah commit folder `.venv/` lokal — build Streamlit Cloud rusak
> kalau ada folder ini (sudah di-cover `.gitignore`).

## Keterbatasan yang jujur

- **Model Whisper `base`** dipilih agar ramah CPU; akurasi turun untuk bicara
  cepat, nama orang, dan bahasa gaul. Video panjang (>10 menit) agak lama di
  hardware free-tier.
- **Kualitas ekstraksi kosakata** tergantung LLM yang tersedia; tanpa API key
  aplikasi memakai tokenisasi heuristik + Google Translate yang bisa kehilangan
  nuansa (bacaan kontekstual, makna percakapan).
- **Unduhan YouTube** bergantung `yt-dlp` mengikuti perubahan situs — kalau
  video gagal, unggah file audio langsung adalah jalur paling andal.
- Ini **alat belajar/portofolio**, bukan pengganti buku teks; selalu periksa
  kosakata hasil ekstraksi sebelum import deck.

## Sumber data & lisensi

- **API OpenAI / LLM kompatibel** untuk enhancement (key sendiri, opsional).
- **Google Translate** via `deep-translator` sebagai fallback gratis.
- **gTTS** untuk audio pelafalan kartu (endpoint TTS Google Translate).
- Kode berlisensi **MIT** — bebas digunakan, dimodifikasi, dan dipelajari.
