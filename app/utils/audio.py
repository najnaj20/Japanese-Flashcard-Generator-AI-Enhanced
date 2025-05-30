import whisper
import yt_dlp
import os
import logging
import warnings
import torch
import shutil
import tempfile
from datetime import datetime
import random
from pathlib import Path

# Mematikan warning yang tidak diperlukan
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.lazy")
warnings.filterwarnings("ignore", message=".*torch.classes.*")

class AudioProcessor:
    def __init__(self, model_type='base'):
        """
        Inisialisasi Audio Processor
        
        Args:
            model_type (str): Tipe model Whisper ('tiny', 'base', 'small', 'medium', 'large')
        """
        # Setup temp directory - menggunakan path relatif
        self.base_dir = Path(os.getcwd())
        self.temp_dir = self.base_dir / "app" / "data" / "temp"
        
        # Pastikan direktori temp ada dan memiliki permission yang benar
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(self.temp_dir), 0o777)
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Setup Whisper model
        self.setup_whisper_model(model_type)

    def _setup_logger(self):
        """Setup logger untuk class"""
        logger = logging.getLogger("app.utils.audio")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _generate_temp_filename(self, prefix="audio_", suffix=".mp3"):
        """Generate nama file temporary yang unik"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        filename = f"{prefix}{timestamp}_{random_suffix}{suffix}"
        return self.temp_dir / filename

    def setup_whisper_model(self, model_type):
        """
        Setup model Whisper
        
        Args:
            model_type (str): Tipe model yang akan digunakan
        """
        try:
            self.logger.info(f"Loading Whisper model: {model_type}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model(model_type, device=device)
            self.logger.info(f"Whisper model loaded successfully on {device}")
        except Exception as e:
            self.logger.error(f"Error loading Whisper model: {str(e)}")
            raise

    def download_youtube_audio(self, url):
        """
        Download audio dari YouTube URL
        
        Args:
            url (str): YouTube URL
            
        Returns:
            Path: Path ke file audio yang didownload
        """
        try:
            output_path = self._generate_temp_filename()
            self.logger.info(f"Downloading audio to: {output_path}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(output_path.with_suffix('')),
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not output_path.exists():
                raise FileNotFoundError(f"Downloaded file not found at {output_path}")
                
            return output_path
            
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            raise

    def transcribe_audio(self, audio_path, language="ja"):
        """
        Transkripsi audio menggunakan Whisper
        
        Args:
            audio_path (Union[str, Path]): Path ke file audio
            language (str): Kode bahasa (default: 'ja' untuk Jepang)
            
        Returns:
            dict: Dictionary berisi transkripsi lengkap
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            self.logger.info(f"Transcribing audio file: {audio_path}")
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe",
                verbose=False
            )
            
            # Mengambil teks dari hasil transkripsi
            if isinstance(result, dict) and 'text' in result:
                full_text = result['text'].strip()
            else:
                # Jika format hasil berbeda, gabungkan teks dari segments
                full_text = ' '.join([segment['text'].strip() for segment in result['segments']])
            
            self.logger.info("Transcription completed successfully")
            return {
                'text': full_text,
                'language': language
            }
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            raise

    def process_youtube_url(self, url, language="ja"):
        """
        Proses YouTube URL: download dan transkripsi
        
        Args:
            url (str): YouTube URL
            language (str): Kode bahasa untuk transkripsi
            
        Returns:
            dict: Dictionary berisi transkripsi lengkap
        """
        audio_path = None
        try:
            self.logger.info(f"Processing YouTube URL: {url}")
            
            # Download audio
            audio_path = self.download_youtube_audio(url)
            self.logger.info(f"Audio downloaded to: {audio_path}")
            
            # Transkripsi audio
            result = self.transcribe_audio(audio_path, language)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing YouTube URL: {str(e)}")
            raise
        finally:
            # Cleanup temporary file
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    self.logger.info(f"Cleaned up temporary audio file: {audio_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temporary file: {str(e)}")

    def process_audio_file(self, file_path, language="ja"):
        """
        Proses file audio yang sudah ada
        
        Args:
            file_path (Union[str, Path]): Path ke file audio
            language (str): Kode bahasa untuk transkripsi
            
        Returns:
            dict: Dictionary berisi transkripsi lengkap
        """
        try:
            file_path = Path(file_path)
            self.logger.info(f"Processing audio file: {file_path}")
            return self.transcribe_audio(file_path, language)
        except Exception as e:
            self.logger.error(f"Error processing audio file: {str(e)}")
            raise

    def cleanup_temp_files(self):
        """Membersihkan file temporary"""
        try:
            if self.temp_dir.exists():
                for file_path in self.temp_dir.glob('audio_*'):
                    try:
                        file_path.unlink()
                        self.logger.info(f"Removed temporary file: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove {file_path}: {str(e)}")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {str(e)}")

    def __del__(self):
        """Destructor untuk membersihkan resources"""
        self.cleanup_temp_files()
