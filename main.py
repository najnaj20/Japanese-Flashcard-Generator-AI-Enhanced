import streamlit as st
import logging
from pathlib import Path
import os
import pandas as pd
from app.utils.audio import AudioProcessor
from app.utils.translator import Translator
from app.utils.vocabulary import VocabularyProcessor
from app.utils.anki import AnkiDeckGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_processors():
    """
    Inisialisasi semua processor yang dibutuhkan aplikasi
    """
    try:
        audio_processor = AudioProcessor(model_type='base')
        translator = Translator()
        vocabulary_processor = VocabularyProcessor()
        anki_creator = AnkiDeckGenerator()

        return audio_processor, translator, vocabulary_processor, anki_creator

    except Exception as e:
        logger.error(f"Error initializing processors: {str(e)}")
        raise

def process_youtube_url(url, audio_processor):
    """
    Proses URL YouTube untuk mendapatkan transkripsi
    """
    try:
        result = audio_processor.process_youtube_url(url)
        return result['text']  # Sekarang result adalah dictionary dengan key 'text'
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {str(e)}")
        st.error(f"Error processing YouTube URL: {str(e)}")
        return None

def process_audio_file(file, audio_processor):
    """
    Proses file audio yang diupload untuk mendapatkan transkripsi
    """
    try:
        temp_dir = Path("app/data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / file.name
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        
        result = audio_processor.process_audio_file(str(temp_path))
        full_text = result['text']  # Sekarang result adalah dictionary dengan key 'text'
        
        os.remove(temp_path)
        
        return full_text
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        st.error(f"Error processing audio file: {str(e)}")
        return None

def create_flashcard(text, translation, vocabulary, anki_creator):
    """
    Buat flashcard dari teks
    """
    try:
        if isinstance(vocabulary, list):
            cards_data = []
            for vocab in vocabulary:
                cards_data.append({
                    'word': vocab,
                    'translation': translation,
                    'context': text
                })
            df = pd.DataFrame(cards_data)
        else:
            data = {
                'word': [vocabulary],
                'translation': [translation],
                'context': [text]
            }
            df = pd.DataFrame(data)
        
        audio_files = anki_creator.create_audio_files(df)
        output_path = anki_creator.generate_deck(df, audio_files)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating flashcard: {str(e)}")
        raise

def download_flashcard(file_path):
    """
    Fungsi untuk menghandle download flashcard
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                file_bytes = file.read()
                st.download_button(
                    label="📥 Download Flashcard (Import ke Anki)",
                    data=file_bytes,
                    file_name="japanese_vocabulary.apkg",
                    mime="application/octet-stream",
                    help="Klik untuk download file flashcard yang bisa diimport ke Anki"
                )
                
                st.info("""
                    📝 Cara import ke Anki:
                    1. Download file flashcard
                    2. Buka aplikasi Anki
                    3. Pilih File > Import
                    4. Pilih file .apkg yang sudah didownload
                    5. Flashcard akan otomatis ditambahkan ke Anki
                """)
        else:
            st.warning("File flashcard belum dibuat")
    except Exception as e:
        logger.error(f"Error downloading flashcard: {str(e)}")
        st.error(f"Error downloading flashcard: {str(e)}")

def main():
    try:
        st.title("Japanese Flashcard Generator")
        
        # Initialize session state
        if 'flashcard_created' not in st.session_state:
            st.session_state.flashcard_created = False
        if 'last_flashcard_path' not in st.session_state:
            st.session_state.last_flashcard_path = None
        
        # Initialize processors
        audio_processor, translator, vocabulary_processor, anki_creator = initialize_processors()
        
        # Input section
        st.header("Input")
        input_type = st.radio(
            "Choose input type:",
            ["YouTube URL", "Audio File"]
        )
        
        transcription_text = None
        
        if input_type == "YouTube URL":
            url = st.text_input("Enter YouTube URL:")
            if url:
                with st.spinner("Processing YouTube video..."):
                    transcription_text = process_youtube_url(url, audio_processor)
                    
        else:  # Audio File
            uploaded_file = st.file_uploader("Upload audio file", type=['mp3', 'wav', 'm4a'])
            if uploaded_file:
                with st.spinner("Processing audio file..."):
                    transcription_text = process_audio_file(uploaded_file, audio_processor)
        
        # Display results
        if transcription_text:
            st.header("Transcription Result")
            st.text_area("Full Transcription", transcription_text, height=200)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Translate"):
                    translation = translator.translate(transcription_text)
                    st.session_state.translation = translation
                    st.write("Translation:")
                    st.write(translation)
            
            with col2:
                if st.button("Create Flashcards"):
                    if 'translation' not in st.session_state:
                        translation = translator.translate(transcription_text)
                        st.session_state.translation = translation
                    else:
                        translation = st.session_state.translation
                        
                    vocabulary = vocabulary_processor.extract_vocabulary(transcription_text)
                    try:
                        output_path = create_flashcard(
                            text=transcription_text,
                            translation=translation,
                            vocabulary=vocabulary,
                            anki_creator=anki_creator
                        )
                        st.success("✅ Flashcards created successfully!")
                        st.session_state.flashcard_created = True
                        st.session_state.last_flashcard_path = output_path
                        download_flashcard(output_path)
                        
                    except Exception as e:
                        st.error(f"Error creating flashcards: {str(e)}")
        
        # Tampilkan tombol download untuk flashcard terakhir yang dibuat
        if st.session_state.flashcard_created and st.session_state.last_flashcard_path:
            st.header("Download Last Created Flashcard")
            download_flashcard(st.session_state.last_flashcard_path)
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An error occurred. Please check the logs for details.")

if __name__ == "__main__":
    main()
