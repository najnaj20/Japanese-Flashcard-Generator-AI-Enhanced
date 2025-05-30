import genanki
import random
import os
import logging
import streamlit as st
from gtts import gTTS
from pathlib import Path
from typing import List, Dict, Union
import pandas as pd

class AnkiDeckGenerator:
    def __init__(self, temp_dir="app/data/temp"):
        """
        Inisialisasi AnkiDeckGenerator
        
        Args:
            temp_dir (str): Path ke direktori temporary untuk menyimpan file audio
        """
        self.logger = logging.getLogger(__name__)
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Gunakan ID yang konsisten untuk model dan deck
        self.model_id = 1963760736  # ID tetap untuk model
        self.deck_id = 1963760737   # ID tetap untuk deck
        
        self.model = self._create_model()
        
        # Inisialisasi status di session state
        if 'current_deck_path' not in st.session_state:
            st.session_state.current_deck_path = None

    def _create_model(self):
        """
        Buat model untuk kartu Anki dengan desain yang lebih baik
        """
        return genanki.Model(
            model_id=self.model_id,
            name='Japanese Vocabulary Model',
            fields=[
                {'name': 'Word'},
                {'name': 'Translation'},
                {'name': 'Context'},
                {'name': 'Audio'}
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '''
                        <div class="card-front">
                            <div class="word">{{Word}}</div>
                            <div class="audio">{{Audio}}</div>
                            <div class="hint">Click to see translation</div>
                        </div>
                    ''',
                    'afmt': '''
                        <div class="card-back">
                            <div class="word">{{Word}}</div>
                            <div class="audio">{{Audio}}</div>
                            <hr>
                            <div class="translation">{{Translation}}</div>
                            <div class="context">Context: {{Context}}</div>
                        </div>
                    ''',
                }
            ],
            css='''
                .card {
                    font-family: "Noto Sans JP", "Hiragino Kaku Gothic Pro", "メイリオ", Meiryo, sans-serif;
                    font-size: 20px;
                    text-align: center;
                    color: #2c3e50;
                    background-color: #ecf0f1;
                    padding: 20px;
                    max-width: 600px;
                    margin: 0 auto;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .card-front, .card-back {
                    padding: 20px;
                }
                .word {
                    font-size: 32px;
                    color: #2980b9;
                    margin: 20px 0;
                    font-weight: bold;
                }
                .translation {
                    font-size: 24px;
                    color: #27ae60;
                    margin: 15px 0;
                }
                .context {
                    font-size: 18px;
                    color: #7f8c8d;
                    margin: 15px 0;
                    font-style: italic;
                    line-height: 1.5;
                }
                .hint {
                    font-size: 14px;
                    color: #95a5a6;
                    margin-top: 20px;
                    font-style: italic;
                }
                hr {
                    border: none;
                    border-top: 2px solid #bdc3c7;
                    margin: 20px 0;
                }
            '''
        )

    def create_audio_files(self, df: pd.DataFrame) -> List[str]:
        """
        Buat file audio untuk setiap kata dengan penanganan error yang lebih baik
        """
        audio_files = []
        try:
            for i, row in df.iterrows():
                word_data = row['word']
                if isinstance(word_data, dict):
                    word = word_data.get('word', '')
                else:
                    word = str(word_data)

                if not word:
                    audio_files.append("")
                    continue

                safe_word = "".join(x for x in word if x.isalnum() or x in (' ', '-', '_'))
                audio_path = self.temp_dir / f"word_{i}_{safe_word}.mp3"
                
                try:
                    # Tambahkan pengecekan file yang sudah ada
                    if not audio_path.exists():
                        tts = gTTS(text=word, lang='ja')
                        tts.save(str(audio_path))
                    audio_files.append(str(audio_path))
                    self.logger.info(f"Audio file ready for: {word}")
                except Exception as e:
                    self.logger.warning(f"Failed to create audio for word '{word}': {str(e)}")
                    audio_files.append("")
                    
            return audio_files
            
        except Exception as e:
            self.logger.error(f"Error creating audio files: {str(e)}")
            raise

    def generate_deck(self, df: pd.DataFrame, audio_files: List[str]) -> str:
        """
        Generate deck Anki dengan penanganan status yang lebih baik
        """
        try:
            deck = genanki.Deck(
                self.deck_id,
                'Japanese Vocabulary from Text'
            )
            
            valid_audio_files = []
            for i, (_, row) in enumerate(df.iterrows()):
                word_data = row['word']
                if isinstance(word_data, dict):
                    word = word_data.get('word', '')
                    reading = word_data.get('reading', '')
                    word_field = f"{word} [{reading}]" if reading else word
                else:
                    word_field = str(word_data)

                audio_path = audio_files[i] if i < len(audio_files) else ""
                
                if audio_path and os.path.exists(audio_path):
                    audio_filename = os.path.basename(audio_path)
                    audio_field = f'[sound:{audio_filename}]'
                    valid_audio_files.append(audio_path)
                else:
                    audio_field = ''

                note = genanki.Note(
                    model=self.model,
                    fields=[
                        word_field,
                        str(row.get('translation', '')),
                        str(row.get('context', '')),
                        audio_field
                    ]
                )
                deck.add_note(note)
                self.logger.info(f"Added note for word: {word_field}")

            # Buat package dengan timestamp untuk menghindari konflik
            output_path = self.temp_dir / f'japanese_vocabulary.apkg'
            
            package = genanki.Package(deck)
            if valid_audio_files:
                package.media_files = valid_audio_files
            
            package.write_to_file(str(output_path))
            
            # Update session state dengan path deck terbaru
            st.session_state.current_deck_path = str(output_path)
            st.session_state.flashcard_created = True
            
            self.logger.info(f"Successfully generated Anki deck at: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Error generating deck: {str(e)}")
            raise

    def cleanup_old_files(self, keep_current=True):
        """
        Membersihkan file lama dengan opsi untuk menyimpan file terbaru
        
        Args:
            keep_current (bool): Jika True, akan menyimpan file deck terbaru
        """
        try:
            current_deck = st.session_state.get('current_deck_path')
            
            # Hapus file audio
            for file in self.temp_dir.glob("*.mp3"):
                try:
                    file.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete audio file {file}: {str(e)}")
            
            # Hapus file deck lama
            for file in self.temp_dir.glob("*.apkg"):
                if keep_current and current_deck and str(file) == current_deck:
                    continue
                try:
                    file.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete deck file {file}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def __del__(self):
        """
        Cleanup saat object dihapus
        """
        self.cleanup_old_files(keep_current=True)
