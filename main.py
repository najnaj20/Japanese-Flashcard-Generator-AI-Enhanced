import streamlit as st

# Tambahkan konfigurasi page SEBELUM logging setup
st.set_page_config(
    page_title="Japanese Flashcard Generator AI",
    page_icon="🇯🇵",
    layout="wide",
    initial_sidebar_state="expanded"
)

import logging
from pathlib import Path
import os
import pandas as pd
import asyncio
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
import re
import time

# Import modules dengan error handling
try:
    from app.utils.audio import AudioProcessor
    from app.utils.translator import JapaneseTranslator
    from app.utils.vocabulary import VocabularyProcessor
    from app.utils.anki import AnkiDeckGenerator
    from app.utils.ai_helper import AIHelper
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.stop()

# Setup directories
log_dir = Path("app/data/temp")
log_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "anki_generator.log")
    ]
)
logger = logging.getLogger(__name__)

# Suppress verbose logging
for logger_name in ['httpx', 'httpcore', 'urllib3', 'openai']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

@dataclass
class ProcessorContainer:
    """Container untuk menyimpan semua processor"""
    audio_processor: AudioProcessor
    translator: JapaneseTranslator
    vocabulary_processor: VocabularyProcessor
    anki_creator: AnkiDeckGenerator
    ai_helper: AIHelper

def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment variables or Streamlit secrets"""
    # Coba ambil dari environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # Jika tidak ada, coba dari Streamlit secrets
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            pass
    
    return api_key

class FlashcardApp:
    def __init__(self):
        """Initialize FlashcardApp with necessary components"""
        self.processors = None
        self._setup_session_state()
        self.temp_dir = Path("app/data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        self._initialize_processors_safely()

    def _setup_session_state(self) -> None:
        """Setup Streamlit session state variables"""
        default_states = {
            'flashcard_created': False,
            'last_flashcard_path': None,
            'vocabulary': [],
            'vocabulary_details': [],
            'processors_initialized': False,
            'transcription_result': None,
            'processing_complete': False,
            'api_key_validated': False
        }
        
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    def _initialize_processors_safely(self) -> None:
        """Initialize all required processors with proper error handling"""
        if st.session_state.processors_initialized and self.processors:
            return
            
        try:
            # Check OpenAI API key first
            openai_api_key = get_openai_api_key()
            if not openai_api_key:
                self._show_api_key_error()
                return
            
            # Show initialization progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize processors step by step
            processors_info = [
                ("Audio Processor", AudioProcessor, {'model_type': 'base'}),
                ("Translator", JapaneseTranslator, {}),
                ("Vocabulary Processor", VocabularyProcessor, {}),
                ("Anki Deck Generator", AnkiDeckGenerator, {}),
                ("AI Helper", AIHelper, {'api_key': openai_api_key, 'model': 'gpt-3.5-turbo'})
            ]
            
            initialized_processors = {}
            
            for i, (name, processor_class, kwargs) in enumerate(processors_info):
                status_text.text(f"Initializing {name}...")
                progress_bar.progress((i + 1) / len(processors_info))
                
                try:
                    processor = processor_class(**kwargs)
                    initialized_processors[name.lower().replace(' ', '_')] = processor
                    logger.info(f"{name} initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize {name}: {e}")
                    st.error(f"❌ Failed to initialize {name}: {e}")
                    return
            
            # Create processor container
            self.processors = ProcessorContainer(
                audio_processor=initialized_processors['audio_processor'],
                translator=initialized_processors['translator'],
                vocabulary_processor=initialized_processors['vocabulary_processor'],
                anki_creator=initialized_processors['anki_deck_generator'],
                ai_helper=initialized_processors['ai_helper']
            )
            
            # Cleanup progress indicators
            progress_bar.empty()
            status_text.empty()
            
            st.session_state.processors_initialized = True
            st.session_state.api_key_validated = True
            logger.info("All processors initialized successfully with OpenAI")
            
        except Exception as e:
            logger.error(f"Error initializing processors: {str(e)}")
            st.error(f"❌ **Initialization failed:** {str(e)}")
            self._show_troubleshooting_tips()

    def _show_api_key_error(self):
        """Show API key error message"""
        st.error("""
        ❌ **OpenAI API Key tidak ditemukan!**
        
        Untuk menggunakan aplikasi ini, Anda perlu:
        
        1. **Dapatkan API Key dari OpenAI:**
           - Kunjungi https://platform.openai.com/api-keys
           - Buat akun atau login
           - Generate API key baru
        
        2. **Set API Key sebagai environment variable:**
           ```bash
           export OPENAI_API_KEY="your-api-key-here"
           ```
        
        3. **Atau tambahkan ke Streamlit secrets:**
           - Buat file `.streamlit/secrets.toml`
           - Tambahkan: `OPENAI_API_KEY = "your-api-key-here"`
        
        4. **Restart aplikasi setelah menambahkan API key**
        """)

    def _show_troubleshooting_tips(self):
        """Show troubleshooting tips"""
        st.info("""
        **Solusi yang bisa dicoba:**
        1. Pastikan OPENAI_API_KEY sudah diset dengan benar
        2. Periksa koneksi internet Anda
        3. Pastikan semua dependencies sudah terinstall
        4. Coba restart aplikasi
        5. Periksa apakah API key masih valid di OpenAI dashboard
        
        **Jika masalah berlanjut:**
        - Periksa log untuk detail error
        - Pastikan quota OpenAI API Anda masih tersedia
        """)

    def _validate_youtube_url(self, url: str) -> bool:
        """Validasi URL YouTube"""
        youtube_regex = (
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        
        if not url or not url.strip():
            st.warning("URL tidak boleh kosong")
            return False
        
        if not re.match(youtube_regex, url):
            st.error("URL YouTube tidak valid. Pastikan menggunakan format URL YouTube yang benar.")
            return False
        
        return True

    def _validate_audio_file(self, file) -> bool:
        """Validasi file audio"""
        if not file:
            st.warning("Tidak ada file yang dipilih")
            return False
        
        allowed_types = ['mp3', 'wav', 'm4a']
        file_ext = file.name.split('.')[-1].lower()
        max_file_size = 200 * 1024 * 1024  # 200 MB
        
        if file_ext not in allowed_types:
            st.error(f"Tipe file tidak didukung. Gunakan {', '.join(allowed_types)}")
            return False
        
        if file.size > max_file_size:
            st.error("Ukuran file melebihi batas 200 MB")
            return False
        
        return True

    async def process_input(self, input_type: str, url: str = None, file=None) -> Optional[str]:
        """Process input based on type and return transcription"""
        if not self.processors:
            st.error("Processors not initialized properly")
            return None
            
        try:
            if input_type == "YouTube URL" and url:
                if not self._validate_youtube_url(url):
                    return None
                return await self._process_youtube_url(url)
            elif input_type == "Audio File" and file:
                if not self._validate_audio_file(file):
                    return None
                return await self._process_audio_file(file)
            return None
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            st.error(f"Error processing input: {str(e)}")
            return None

    async def _process_youtube_url(self, url: str) -> Optional[str]:
        """Process YouTube URL and return transcription"""
        try:
            with st.spinner("🎥 Processing YouTube URL..."):
                # Add progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Downloading audio...")
                progress_bar.progress(0.3)
                
                result = self.processors.audio_processor.process_youtube_url(url)
                
                progress_bar.progress(0.8)
                status_text.text("Transcribing audio...")
                
                progress_bar.progress(1.0)
                status_text.text("Complete!")
                
                # Cleanup
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
                return result.get('text', '')
        except Exception as e:
            logger.error(f"Error processing YouTube URL: {str(e)}")
            st.error(f"Failed to process YouTube URL: {str(e)}")
            return None

    async def _process_audio_file(self, file) -> Optional[str]:
        """Process audio file and return transcription"""
        temp_path = self.temp_dir / file.name
        try:
            with st.spinner("🎵 Processing audio file..."):
                # Save uploaded file
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                
                # Process audio
                result = self.processors.audio_processor.process_audio_file(str(temp_path))
                return result.get('text', '')
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            st.error(f"Failed to process audio file: {str(e)}")
            return None
        finally:
            # Cleanup temp file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")

    async def create_flashcard_from_details(self, text: str, vocabulary_details: List[Dict]) -> str:
        """Create flashcard dari vocabulary details yang sudah lengkap"""
        if not self.processors:
            raise RuntimeError("Processors not initialized")
            
        try:
            # Validation
            if not vocabulary_details:
                raise ValueError("No vocabulary details provided")
            
            # Convert to DataFrame
            df = pd.DataFrame(vocabulary_details)
            
            # Validate required columns
            required_columns = ['kanji', 'kana', 'arti']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            with st.spinner("🎵 Creating audio files..."):
                audio_files = self.processors.anki_creator.create_audio_files(df)
            
            with st.spinner("📚 Creating Anki deck..."):
                return self.processors.anki_creator.generate_deck(df, audio_files)
                
        except Exception as e:
            logger.error(f"Error creating flashcard: {str(e)}")
            raise

    def render_ui(self):
        """Render the main UI components"""
        st.title("🇯🇵 Japanese Flashcard Generator AI-Enhanced")
        st.markdown("*Powered by OpenAI GPT for enhanced vocabulary learning*")
        
        # Check initialization status
        if not st.session_state.processors_initialized:
            st.warning("⏳ Initializing application components...")
            self._initialize_processors_safely()
            if st.session_state.processors_initialized:
                st.success("✅ Application initialized successfully with OpenAI!")
                st.rerun()
            else:
                st.stop()
        
        input_type = self._render_input_section()
        self._render_sidebar()
        return input_type

    def _render_input_section(self):
        """Render input section of the UI"""
        st.header("📥 Input")
        
        # Input type selection
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Choose input type:**")
        
        input_type = st.radio(
            "", 
            ["YouTube URL", "Audio File"], 
            index=0,
            key="input_type_selection",
            horizontal=True
        )
        return input_type

    def _render_sidebar(self):
        """Render sidebar information"""
        with st.sidebar:
            st.header("🤖 About OpenAI Enhancement")
            st.info("""
                This version uses **OpenAI GPT** to enhance flashcards with:
                
                ✨ **Rich Content**
                - Kanji & Kana readings
                - Accurate translations
                - Natural example sentences
                - JLPT level estimation
                - Word categories
                
                🎯 **Learning Focus**
                - Context-aware examples
                - Natural usage patterns
                - Proper pronunciation
                
                🔄 **AI-Powered Features**
                - GPT-3.5 Turbo for fast processing
                - Intelligent vocabulary extraction
                - Quality-checked results
                - Consistent formatting
            """)
            
            # Model Information
            st.header("🔧 Model Information")
            if st.session_state.processors_initialized and self.processors:
                model_name = getattr(self.processors.ai_helper, 'model', 'gpt-3.5-turbo')
                st.success(f"**Model:** {model_name}")
                st.success("**Status:** ✅ Ready")
            else:
                st.warning("**Status:** ⏳ Initializing...")
            
            # Usage Tips
            st.header("💡 Usage Tips")
            st.markdown("""
            **For best results:**
            - Use clear Japanese audio
            - Keep videos under 10 minutes
            - Check extracted vocabulary before creating flashcards
            - Import .apkg files directly to Anki
            """)
            
            # Clear all data button
            if st.button("🗑️ Clear All Data", key="clear_all_data"):
                self._clear_all_session_data()
                st.success("✅ All data cleared!")
                st.rerun()

    def _clear_all_session_data(self):
        """Clear all session state data"""
        keys_to_clear = [
            'transcription_result', 'processing_complete', 'vocabulary', 
            'vocabulary_details', 'flashcard_created', 'last_flashcard_path'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    @staticmethod
    def download_flashcard(file_path: str):
        """Handle flashcard download"""
        try:
            if not Path(file_path).exists():
                st.error("Flashcard file not found")
                return
                
            with open(file_path, "rb") as file:
                st.download_button(
                    label="📥 Download Flashcard (Import ke Anki)",
                    data=file.read(),
                    file_name="japanese_vocabulary_openai_enhanced.apkg",
                    mime="application/octet-stream",
                    help="Klik untuk download file flashcard yang bisa diimport ke Anki"
                )
            
            with st.expander("📝 Cara Import ke Anki", expanded=False):
                st.markdown("""
                **Langkah-langkah:**
                1. Download file flashcard
                2. Buka aplikasi Anki
                3. Pilih File > Import
                4. Pilih file .apkg yang sudah didownload
                5. Flashcard akan otomatis ditambahkan ke Anki
                
                **Fitur Flashcard:**
                - ✅ Kanji dan cara bacanya
                - ✅ Arti dalam Bahasa Indonesia
                - ✅ Contoh kalimat dengan terjemahan
                - ✅ Level JLPT
                - ✅ Kategori kata
                - ✅ Audio pengucapan
                """)
        except Exception as e:
            logger.error(f"Error downloading flashcard: {str(e)}")
            st.error("Error downloading flashcard. Please try again.")

async def main():
    """Main application entry point"""
    try:
        app = FlashcardApp()
        
        # Render UI dan dapatkan input type
        input_type = app.render_ui()
        
        # Only proceed if processors are initialized
        if not st.session_state.processors_initialized:
            return
        
        # Handle input berdasarkan type
        transcription_text = None
        
        if input_type == "YouTube URL":
            st.subheader("🎥 YouTube Video Processing")
            url = st.text_input(
                "Enter YouTube URL:",
                placeholder="https://www.youtube.com/watch?v=example",
                key="youtube_url_input"
            )
            
            if url and st.button("🎥 Process YouTube URL", key="process_youtube_btn", type="primary"):
                transcription_text = await app.process_input("YouTube URL", url=url)
                if transcription_text:
                    st.session_state.transcription_result = transcription_text
                    st.session_state.processing_complete = True
                    st.success("✅ YouTube video processed successfully!")
                else:
                    st.error("Failed to process YouTube video. Please check the URL and try again.")
        
        else:  # Audio File
            st.subheader("🎵 Audio File Processing")
            uploaded_file = st.file_uploader(
                "Upload audio file", 
                type=['mp3', 'wav', 'm4a'],
                help="Limit 200MB per file • MP3, WAV, M4A",
                key="audio_file_uploader"
            )
            
            if uploaded_file:
                # Show file info
                file_size_mb = uploaded_file.size / (1024 * 1024)
                st.info(f"📁 **File:** {uploaded_file.name} ({file_size_mb:.1f} MB)")
                
                if st.button("🎵 Process Audio File", key="process_audio_btn", type="primary"):
                    transcription_text = await app.process_input("Audio File", file=uploaded_file)
                    if transcription_text:
                        st.session_state.transcription_result = transcription_text
                        st.session_state.processing_complete = True
                        st.success("✅ Audio file processed successfully!")
                    else:
                        st.error("Failed to process audio file. Please try again.")

        # Display transcription results
        display_text = transcription_text or st.session_state.get('transcription_result')
        
        if display_text:
            st.header("📝 Transcription Result")
            
            # Show transcription with copy button
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_area(
                    "Full Transcription", 
                    display_text, 
                    height=200,
                    key="transcription_display"
                )
            with col2:
                if st.button("📋 Copy", key="copy_transcription"):
                    st.code(display_text)
                    st.success("Text ready to copy!")
            
            # Action buttons
            st.subheader("🎯 Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Extract Vocabulary", key="extract_vocab_btn", type="secondary"):
                    with st.spinner("🤖 Mengekstrak kosakata dengan OpenAI..."):
                        try:
                            vocabulary_details = await app.processors.ai_helper.extract_vocabulary_from_transcript(display_text)
                            
                            if vocabulary_details:
                                st.session_state.vocabulary_details = vocabulary_details
                                vocabulary_words = [item.get('kanji', item.get('word', '')) for item in vocabulary_details]
                                st.session_state.vocabulary = vocabulary_words
                                
                                st.success(f"✅ Extracted {len(vocabulary_details)} vocabulary items!")
                                
                                # Display vocabulary in a nice format
                                st.subheader("📋 Extracted Vocabulary")
                                for i, item in enumerate(vocabulary_details, 1):
                                    kanji = item.get('kanji', item.get('word', ''))
                                    kana = item.get('kana', item.get('reading', ''))
                                    arti = item.get('arti', item.get('meaning', ''))
                                    
                                    with st.container():
                                        st.markdown(f"**{i}. {kanji}** ({kana}) - {arti}")
                                
                                # Show detailed view
                                with st.expander("🔍 Detailed View", expanded=False):
                                    st.dataframe(pd.DataFrame(vocabulary_details), use_container_width=True)
                            else:
                                st.warning("Tidak ada kosakata yang berhasil diekstrak. Coba dengan teks yang berbeda.")
                        except Exception as e:
                            st.error(f"Error extracting vocabulary: {str(e)}")
            
            with col2:
                if st.button("🎴 Create AI-Enhanced Flashcards", key="create_flashcards_btn", type="primary"):
                    try:
                        # Check if vocabulary is already extracted
                        if not st.session_state.get('vocabulary_details'):
                            with st.spinner("🤖 Mengekstrak kosakata dengan OpenAI..."):
                                vocabulary_details = await app.processors.ai_helper.extract_vocabulary_from_transcript(display_text)
                                st.session_state.vocabulary_details = vocabulary_details
                                vocabulary_words = [item.get('kanji', item.get('word', '')) for item in vocabulary_details]
                                st.session_state.vocabulary = vocabulary_words
                        
                        if st.session_state.vocabulary_details:
                            output_path = await app.create_flashcard_from_details(
                                text=display_text,
                                vocabulary_details=st.session_state.vocabulary_details
                            )
                            st.success("✅ AI-Enhanced Flashcards created successfully!")
                            st.session_state.flashcard_created = True
                            st.session_state.last_flashcard_path = output_path
                            
                            # Show download immediately
                            st.subheader("📥 Download Your Flashcards")
                            app.download_flashcard(output_path)
                        else:
                            st.error("No vocabulary found. Please extract vocabulary first.")
                    except Exception as e:
                        logger.error(f"Error creating flashcards: {str(e)}")
                        st.error(f"Error creating flashcards: {str(e)}")
            
            with col3:
                if st.button("🗑️ Clear Results", key="clear_results_btn"):
                    app._clear_all_session_data()
                    st.success("✅ Results cleared!")
                    st.rerun()

        # Display download section for last created flashcard
        if st.session_state.get('flashcard_created') and st.session_state.get('last_flashcard_path'):
            if not display_text:  # Only show if not already shown above
                st.header("📥 Download Last Created Flashcard")
                app.download_flashcard(st.session_state.last_flashcard_path)

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        st.info("Please try refreshing the page or contact support if the problem persists.")

def run_async_main():
    """Wrapper to run async main function in Streamlit"""
    try:
        # Check if there's already a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If loop is already running, create a new thread
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(main())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=300)  # 5 minute timeout
        else:
            # Run directly
            return asyncio.run(main())
        
    except Exception as e:
        logger.error(f"Fatal error in async main: {e}")
        st.error(f"Aplikasi mengalami kesalahan fatal: {e}")
        st.stop()

if __name__ == "__main__":
    run_async_main()
