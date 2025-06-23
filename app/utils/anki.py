from __future__ import annotations
import genanki
import random
import os
import logging
import streamlit as st
from gtts import gTTS
from pathlib import Path
from typing import List, Dict, Union, Optional
from dataclasses import dataclass
import pandas as pd
import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import shutil

@dataclass
class ExampleSentence:
    """Data class untuk contoh kalimat"""
    kalimat: str
    kana: str
    arti: str

@dataclass
class VocabularyCard:
    """Data class untuk kartu kosakata"""
    kanji: str
    kana: str
    romaji: str
    arti: str
    contoh: ExampleSentence
    level: str
    kategori: str
    audio_path: Optional[str] = None

class AnkiDeckConfig:
    """Konfigurasi untuk Anki Deck"""
    MODEL_ID = 1963760736
    DECK_ID = 1963760737
    DECK_NAME = 'Japanese Vocabulary Enhanced'
    CSS_FILE = 'app/static/anki_style.css'

class AnkiDeckGenerator:
    def __init__(self, deck_name="Japanese Vocabulary", model_name="Japanese Vocabulary", temp_dir="app/data/temp", max_workers=4):
        self.deck_name = deck_name
        self.model_name = model_name
        self.temp_dir = Path(temp_dir)
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
        # ✅ PERBAIKAN UTAMA: Buat model sebagai genanki.Model object
        self.model = self._create_model()
        
        self.initialize_directories()

    def setup_logging(self) -> None:
        """Setup logging configuration"""
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        fh = logging.FileHandler('anki_generator.log')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def initialize_directories(self) -> None:
        """Initialize necessary directories"""
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.audio_dir = self.temp_dir / 'audio'
            self.audio_dir.mkdir(exist_ok=True)
            # Buat direktori untuk file sementara Anki
            self.anki_temp_dir = self.temp_dir / 'anki_temp'
            self.anki_temp_dir.mkdir(exist_ok=True)
            self.logger.info(f"Initialized directories at {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"Failed to initialize directories: {e}")
            raise RuntimeError(f"Directory initialization failed: {e}")

    def initialize_session_state(self) -> None:
        """Initialize Streamlit session state"""
        if 'current_deck_path' not in st.session_state:
            st.session_state.current_deck_path = None

    def _get_default_css(self) -> str:
        """Return default CSS if CSS file not found"""
        return """
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
        .kanji {
            font-size: 30px;
            color: #1a73e8;
            font-weight: bold;
        }
        .kana {
            font-size: 24px;
            color: #34a853;
        }
        .meaning {
            font-size: 22px;
            color: #4285f4;
            margin: 10px 0;
        }
        .example {
            font-style: italic;
            color: #5f6368;
            margin: 15px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .meta {
            font-size: 14px;
            color: #666;
            margin: 5px 0;
        }
        """
    
    def _load_css(self) -> str:
        """Load CSS from external file"""
        try:
            css_path = Path(AnkiDeckConfig.CSS_FILE)
            if css_path.exists():
                with open(css_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"CSS file not found: {css_path}")
                return self._get_default_css()
        except Exception as e:
            self.logger.warning(f"Failed to load CSS file: {e}")
            return self._get_default_css()

    def _create_model(self) -> genanki.Model:
        """✅ PERBAIKAN: Create Anki card model sebagai genanki.Model object"""
        try:
            return genanki.Model(
                model_id=AnkiDeckConfig.MODEL_ID,
                name='Japanese Vocabulary Model Enhanced',
                fields=[
                    {'name': 'Kanji'},
                    {'name': 'Kana'},
                    {'name': 'Romaji'},
                    {'name': 'Arti'},
                    {'name': 'Contoh_Kalimat'},
                    {'name': 'Contoh_Kana'},
                    {'name': 'Contoh_Arti'},
                    {'name': 'Level'},
                    {'name': 'Kategori'},
                    {'name': 'Audio'}
                ],
                templates=[self._get_card_template()],
                css=self._load_css()
            )
        except Exception as e:
            self.logger.error(f"Failed to create model: {e}")
            raise

    def _get_question_format(self) -> str:
        """Get question format template"""
        return """
        <div class="kanji">{{Kanji}}</div>
        <div class="kana">{{Kana}}</div>
        {{#Audio}}{{Audio}}{{/Audio}}
        """

    def _get_answer_format(self) -> str:
        """Get answer format template"""
        return """
        <div class="kanji">{{Kanji}}</div>
        <div class="kana">{{Kana}}</div>
        {{#Audio}}{{Audio}}{{/Audio}}
        <hr id="answer">
        <div class="meaning">{{Arti}}</div>
        <div class="meta">Romaji: {{Romaji}}</div>
        <div class="meta">Level: {{Level}} | Kategori: {{Kategori}}</div>
        {{#Contoh_Kalimat}}
        <div class="example">
            <div><strong>Contoh:</strong></div>
            <div>{{Contoh_Kalimat}}</div>
            <div>{{Contoh_Kana}}</div>
            <div><em>{{Contoh_Arti}}</em></div>
        </div>
        {{/Contoh_Kalimat}}
        """

    def _get_card_template(self) -> dict:
        """Get card template configuration"""
        return {
            'name': 'Card 1',
            'qfmt': self._get_question_format(),
            'afmt': self._get_answer_format()
        }

    def _create_audio_file(self, text: str, index: int) -> Optional[str]:
        """Create single audio file"""
        try:
            if not text:
                return None

            # Sanitize filename
            safe_text = "".join(x for x in text if x.isalnum() or x in (' ', '-', '_'))
            safe_text = safe_text.replace(' ', '_')[:20]  # Limit length
            audio_path = self.audio_dir / f"word_{index}_{safe_text}.mp3"

            if not audio_path.exists():
                tts = gTTS(text=text, lang='ja')
                tts.save(str(audio_path))
            
            return str(audio_path)
        except Exception as e:
            self.logger.warning(f"Failed to create audio for '{text}': {e}")
            return None

    def create_audio_files(self, df: pd.DataFrame) -> Dict[int, str]:
        """Create audio files in parallel"""
        audio_files = {}
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    i: executor.submit(
                        self._create_audio_file, 
                        row.get('kana', ''), 
                        i
                    )
                    for i, row in df.iterrows()
                }
                
                for i, future in futures.items():
                    try:
                        result = future.result()
                        if result:
                            audio_files[i] = result
                    except Exception as e:
                        self.logger.warning(f"Failed to process audio for index {i}: {e}")
                
            return audio_files
            
        except Exception as e:
            self.logger.error(f"Error in audio file creation: {e}")
            raise

    def _create_note(self, vocab: VocabularyCard) -> genanki.Note:
        """✅ PERBAIKAN: Create individual Anki note dengan model object"""
        audio_field = f'[sound:{os.path.basename(vocab.audio_path)}]' if vocab.audio_path else ''
        
        return genanki.Note(
            model=self.model,  # ✅ Menggunakan self.model (genanki.Model object)
            fields=[
                str(vocab.kanji),
                str(vocab.kana),
                str(vocab.romaji),
                str(vocab.arti),
                str(vocab.contoh.kalimat),
                str(vocab.contoh.kana),
                str(vocab.contoh.arti),
                str(vocab.level),
                str(vocab.kategori),
                audio_field
            ]
        )

    def generate_deck(self, df: pd.DataFrame, audio_files: Dict[int, str]) -> str:
        """Generate enhanced Anki deck"""
        try:
            deck = genanki.Deck(
                AnkiDeckConfig.DECK_ID,
                AnkiDeckConfig.DECK_NAME
            )
            
            valid_audio_files = []
            
            for i, row in df.iterrows():
                vocab_card = self._create_vocabulary_card(row, audio_files.get(i))
                note = self._create_note(vocab_card)
                deck.add_note(note)
                
                if vocab_card.audio_path and os.path.exists(vocab_card.audio_path):
                    valid_audio_files.append(vocab_card.audio_path)
                
                self.logger.info(f"Added note for: {vocab_card.kanji}")

            output_path = self._save_deck(deck, valid_audio_files)
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error generating deck: {e}")
            raise

    def _create_vocabulary_card(self, row: pd.Series, audio_path: Optional[str]) -> VocabularyCard:
        """Create VocabularyCard from DataFrame row"""
        # Handle contoh_kalimat yang mungkin berupa list atau dict
        contoh_data = row.get('contoh_kalimat', [])
        if isinstance(contoh_data, list) and len(contoh_data) > 0:
            contoh = contoh_data[0]
        elif isinstance(contoh_data, dict):
            contoh = contoh_data
        else:
            contoh = {}
            
        return VocabularyCard(
            kanji=str(row.get('kanji', '')),
            kana=str(row.get('kana', '')),
            romaji=str(row.get('romaji', '')),
            arti=str(row.get('arti', '')),
            contoh=ExampleSentence(
                kalimat=str(contoh.get('kalimat', '')),
                kana=str(contoh.get('kana', '')),
                arti=str(contoh.get('arti', ''))
            ),
            level=str(row.get('level', '')),
            kategori=str(row.get('kategori', '')),
            audio_path=audio_path
        )

    def _save_deck(self, deck: genanki.Deck, media_files: List[str]) -> Path:
        """Save deck to file"""
        output_path = self.anki_temp_dir / 'japanese_vocabulary_enhanced.apkg'
        
        package = genanki.Package(deck)
        if media_files:
            # Filter only existing files
            existing_files = [f for f in media_files if os.path.exists(f)]
            package.media_files = existing_files
        
        package.write_to_file(str(output_path))
        
        # Update session state
        st.session_state.current_deck_path = str(output_path)
        st.session_state.flashcard_created = True
        
        self.logger.info(f"Deck saved to: {output_path}")
        return output_path

    def cleanup_old_files(self, keep_current=True):
        """Hapus file lama di dalam direktori"""
        try:
            # Hapus file audio lama
            if hasattr(self, 'audio_dir') and self.audio_dir.exists():
                for file in self.audio_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
                self.logger.info("File audio lama telah dihapus")
            
            # Hapus file sementara Anki
            if hasattr(self, 'anki_temp_dir') and self.anki_temp_dir.exists():
                for file in self.anki_temp_dir.glob('*'):
                    if file.is_file() and keep_current:
                        # Skip current deck file
                        if hasattr(st.session_state, 'current_deck_path'):
                            if str(file) != st.session_state.current_deck_path:
                                file.unlink()
                        else:
                            file.unlink()
                    elif not keep_current:
                        file.unlink()
                self.logger.info("File sementara Anki telah dihapus")
                
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")

    def cleanup(self):
        """Cleanup temporary files"""
        try:
            if hasattr(self, 'audio_dir') and self.audio_dir.exists():
                shutil.rmtree(self.audio_dir)
                self.logger.info("Cleaned up audio directory")

            if hasattr(self, 'anki_temp_dir') and self.anki_temp_dir.exists():
                shutil.rmtree(self.anki_temp_dir)
                self.logger.info("Cleaned up anki temp directory")
                            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup on object destruction"""
        try:
            self.cleanup_old_files(keep_current=True)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error in destructor: {e}")
