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
import time
import glob
from pathlib import Path
import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



ssl._create_default_https_context = ssl._create_unverified_context
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
        
        # Buat direktori khusus untuk cache Whisper
        self.whisper_cache_dir = self.temp_dir / "whisper_cache"
        self.whisper_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Set environment variable untuk cache Whisper
        os.environ['WHISPER_CACHE_DIR'] = str(self.whisper_cache_dir)
        os.environ['XDG_CACHE_HOME'] = str(self.whisper_cache_dir)
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Setup Whisper model
        self.setup_whisper_model(model_type)

    def _setup_logger(self):
        """Setup logger untuk class"""
        logger = logging.getLogger("app.utils.audio")
        logger.setLevel(logging.DEBUG)  # Ubah ke DEBUG untuk informasi lebih detail
        
        # Hapus handler lama jika ada
        if logger.handlers:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # File Handler (opsional)
        try:
            log_dir = self.base_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / "audio_processor.log")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Could not create file logger: {e}")
        
        logger.addHandler(console_handler)
        
        return logger


    def _generate_temp_filename(self, prefix="audio_", suffix=".mp3"):
        """Generate nama file temporary yang unik"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = random.randint(1000, 9999)
        filename = f"{prefix}{timestamp}_{random_suffix}{suffix}"
        return self.temp_dir / filename

    def setup_whisper_model(self, model_type):
        """
        Setup model Whisper dengan handling cache directory yang proper
        
        Args:
            model_type (str): Tipe model yang akan digunakan
        """
        try:
            self.logger.info(f"Loading Whisper model: {model_type}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Set download root untuk model Whisper
            download_root = str(self.whisper_cache_dir)
            
            # Load model dengan cache directory yang sudah ditentukan
            self.model = whisper.load_model(
                model_type, 
                device=device,
                download_root=download_root
            )
            
            self.logger.info(f"Whisper model loaded successfully on {device}")
            self.logger.info(f"Model cache directory: {download_root}")
            
        except PermissionError as e:
            self.logger.error(f"Permission error loading Whisper model: {str(e)}")
            # Fallback ke temporary directory system
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    self.model = whisper.load_model(
                        model_type, 
                        device=device,
                        download_root=temp_dir
                    )
                    self.logger.info(f"Whisper model loaded with temporary directory fallback")
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {str(fallback_error)}")
                raise
        except Exception as e:
            self.logger.error(f"Error loading Whisper model: {str(e)}")
            # Coba alternatif lain
            try:
                # Gunakan home directory sebagai cache
                home_cache = Path.home() / ".cache" / "whisper"
                home_cache.mkdir(parents=True, exist_ok=True)
                
                self.model = whisper.load_model(
                    model_type, 
                    device=device,
                    download_root=str(home_cache)
                )
                self.logger.info(f"Whisper model loaded using home cache directory")
            except Exception as final_error:
                self.logger.error(f"All loading attempts failed: {str(final_error)}")
                raise

    def download_youtube_audio(self, url, max_retries=3):
        """
        Download audio dari YouTube URL dengan mekanisme retry dan validasi

        Args:
            url (str): YouTube URL
            max_retries (int, optional): Jumlah maksimal percobaan download. Default 3.
            
        Returns:
            Path: Path ke file audio yang didownload
        
        Raises:
            ValueError: Jika URL tidak valid
            Exception: Jika gagal download setelah beberapa percobaan
        """
        # Validasi URL YouTube
        def validate_youtube_url(url):
            import re
            youtube_regex = (
                r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
                r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
            )
            if not re.match(youtube_regex, url):
                raise ValueError("URL YouTube tidak valid")

        # Fungsi untuk mendapatkan user agent acak
        def get_random_user_agent():
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
            ]
            import random
            return random.choice(user_agents)

        # Validasi input
        if not url:
            raise ValueError("URL tidak boleh kosong")
        
        validate_youtube_url(url)

        # Iterasi dengan mekanisme retry
        for attempt in range(max_retries):
            try:
                # Generate path output
                output_path = self._generate_temp_filename(suffix='.mp3')
                self.logger.info(f"Percobaan download {attempt + 1}: {output_path}")

                # Konfigurasi yt-dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': str(output_path).replace('.mp3', ''),
                    'no_warnings': True,
                    'ignoreerrors': False,
                    'no_color': True,
                    'quiet': False,
                    'no_check_certificate': True,
                    'verbose': True,
                    'retries': 3,  # Tambahan retry internal
                    'fragment_retries': 3,
                    'http_chunk_size': 10 * 1024 * 1024,  # 10MB chunk
                    
                    # Header dengan user agent acak
                    'http_headers': {
                        'User-Agent': get_random_user_agent(),
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.youtube.com/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    }
                }

                # Proses download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    
                    if not os.path.exists(output_path):
                    # Coba temukan file yang baru saja di-download
                        downloaded_files = glob.glob(str(output_path.parent / f"{output_path.stem}*{output_path.suffix}"))
                        
                        if downloaded_files:
                            output_path = Path(downloaded_files[0])
                        else:
                            raise FileNotFoundError("Tidak dapat menemukan file audio")

                    # Validasi ukuran file
                    if os.path.getsize(output_path) < 1024:  # Kurang dari 1 KB
                        raise ValueError("File audio terlalu kecil")

                    self.logger.info(f"Berhasil download: {info_dict.get('title', 'Unknown Title')}")
                    return output_path

            except Exception as e:
                self.logger.warning(f"Gagal download (Percobaan {attempt + 1}): {e}")
                
                # Tambahkan jeda antara percobaan
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                self.logger.warning(f"Gagal download (Percobaan {attempt + 1}): {error_msg}")

                # Penanganan spesifik untuk error 403
                if "HTTP Error 403" in error_msg:
                    import time
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                    continue

            except Exception as e:
                self.logger.error(f"Error download audio: {e}", exc_info=True)
                
                # Jika percobaan terakhir
                if attempt == max_retries - 1:
                    raise

        # Jika semua percobaan gagal
        raise Exception(f"Gagal download audio setelah {max_retries} percobaan")


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
        try:
            self.cleanup_temp_files()
        except:
            pass  # Silent fail pada destructor