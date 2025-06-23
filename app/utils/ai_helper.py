import os
import json
import logging
import asyncio
import random
import time
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, OpenAI

class AIHelper:
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """
        Inisialisasi AIHelper dengan OpenAI API
        
        Args:
            api_key (str, optional): OpenAI API key. Jika None, akan menggunakan environment variable OPENAI_API_KEY
            model (str, optional): Model OpenAI yang digunakan. Default adalah "gpt-3.5-turbo"
        """
        self.logger = self._setup_logger()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            self.logger.warning("API key tidak ditemukan. Pastikan OPENAI_API_KEY diatur di environment variables")
        
        # Inisialisasi klien async
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        # Inisialisasi klien sync untuk penggunaan dalam fungsi yang bukan async
        self.sync_client = OpenAI(api_key=self.api_key)
        
        # Simpan nama model
        self.model = model
        self.logger.info(f"AIHelper diinisialisasi dengan model {model}")
    
    def _setup_logger(self):
        """Setup logger untuk class"""
        logger = logging.getLogger("app.utils.ai_helper") 
        logger.setLevel(logging.INFO)
        
        if not logger.handlers: 
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    async def _call_openai_with_retry(self, messages, max_retries=3, **kwargs):
        """
        Memanggil OpenAI API dengan mekanisme retry
        
        Args:
            messages (List[Dict]): Daftar pesan untuk API OpenAI
            max_retries (int): Jumlah maksimum percobaan jika terjadi error
            **kwargs: Parameter tambahan untuk OpenAI API
        
        Returns:
            response: Respons dari OpenAI API
        """
        retry_count = 0
        base_delay = 2  # dalam detik
        
        while retry_count < max_retries:
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs
                )
                return response
                
            except Exception as e:
                retry_count += 1
                error_message = str(e)
                
                # Periksa apakah ini rate limit
                if "rate limit" in error_message.lower() or "quota" in error_message.lower():
                    if retry_count >= max_retries:
                        self.logger.error(f"Batas maksimum percobaan tercapai setelah {max_retries} kali. API rate limit masih berlaku.")
                        raise Exception(f"Batas maksimum percobaan tercapai setelah {max_retries} kali. API rate limit masih berlaku.")
                    
                    # Exponential backoff dengan jitter
                    delay = base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                    self.logger.warning(f"Rate limit terdeteksi, mencoba ulang dalam {delay:.2f} detik (percobaan {retry_count}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # Error lain, raise langsung
                    self.logger.error(f"Error pada OpenAI API: {error_message}")
                    raise

    def _create_optimized_prompt(self, text, max_tokens=2000):
        """
        Mengoptimalkan prompt untuk menghemat token
        """
        # Hitung perkiraan token (estimasi kasar: 1 token ≈ 4 karakter)
        estimated_tokens = len(text) / 4
        
        if estimated_tokens > max_tokens:
            # Jika terlalu panjang, potong teks
            # Simpan 75% token untuk teks, 25% untuk instruksi
            chars_to_keep = int(max_tokens * 4 * 0.75)
            truncated_text = text[:chars_to_keep] + "..."
            self.logger.info(f"Mengoptimalkan prompt: memotong dari ~{int(estimated_tokens)} token menjadi ~{max_tokens} token")
            return truncated_text
        
        return text

    def _get_alternative_model(self):
        """
        Mendapatkan model alternatif jika model utama tidak tersedia
        """
        current_model = self.model
        alternatives = {
            "gpt-4": "gpt-3.5-turbo",
            "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-0125": "gpt-3.5-turbo-1106"
        }
        return alternatives.get(current_model)

    async def extract_vocabulary_with_fallback(self, transcript: str, max_vocab=5) -> List[Dict]:
        """
        Ekstrak kosakata dengan fallback ke model alternatif jika terjadi rate limit
        """
        try:
            # Coba dengan model utama terlebih dahulu
            return await self.extract_vocabulary_from_transcript(transcript, max_vocab)
        except Exception as e:
            if "Batas kuota harian tercapai" in str(e) or "rate limit" in str(e).lower():
                self.logger.warning("Mencoba dengan model alternatif karena batas kuota tercapai")
                
                # Simpan model asli
                original_model = self.model
                
                try:
                    # Coba dengan model alternatif
                    alternative_model = self._get_alternative_model()
                    if alternative_model:
                        self.model = alternative_model
                        return await self.extract_vocabulary_from_transcript(transcript, max_vocab)
                    else:
                        raise Exception("Tidak ada model alternatif yang tersedia")
                finally:
                    # Kembalikan model asli
                    self.model = original_model
            
            # Jika bukan masalah kuota atau tidak ada model alternatif, lempar kembali exception
            raise

    def _default_vocabulary_structure(self, word: str) -> Dict:
        """Struktur default jika gagal generate atau terjadi error."""
        return {
            "kanji": word, 
            "kana": word, 
            "romaji": "",
            "arti": "Detail tidak dapat dibuat karena terjadi kesalahan.",
            "contoh_kalimat": [],
            "level": "Tidak diketahui",
            "kategori": "Tidak diketahui"
        }

    async def generate_vocabulary_details(self, word: str) -> Dict:
        """
        Generate detail kosakata menggunakan OpenAI API secara non-blocking.
        
        Args:
            word (str): Kata dalam bahasa Jepang
            
        Returns:
            Dict: Dictionary berisi detail kosakata
        """
        system_prompt = """
        Kamu adalah asisten bahasa Jepang yang ahli. Berikan informasi detail tentang kata bahasa Jepang
        yang diberikan dalam format JSON yang tepat.
        """
        
        user_prompt = f"""
        Berikan detail lengkap untuk kata bahasa Jepang berikut: "{word}"
        
        Berikan dalam format JSON berikut:
        {{
            "kanji": "kata dalam bentuk kanji (jika ada)",
            "kana": "cara baca dalam hiragana",
            "romaji": "penulisan dalam romaji",
            "arti": "arti dalam bahasa Indonesia",
            "contoh_kalimat": [
                {{
                    "kalimat": "contoh kalimat dalam bahasa Jepang",
                    "kana": "cara baca contoh kalimat",
                    "arti": "arti contoh kalimat dalam bahasa Indonesia"
                }}
            ],
            "level": "tingkat kesulitan (N5, N4, N3, N2, N1)",
            "kategori": "jenis kata (Kata Kerja, Kata Benda, dll)"
        }}
        
        Berikan HANYA JSON, tidak ada teks tambahan.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self._call_openai_with_retry(
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            # Membersihkan output dari markdown code block jika ada
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            return json.loads(content)

        except json.JSONDecodeError as json_e:
            self.logger.error(f"JSONDecodeError generating vocabulary details for '{word}': {json_e}")
            return self._default_vocabulary_structure(word)
        except Exception as e:
            self.logger.error(f"Error generating vocabulary details for '{word}': {str(e)}")
            return self._default_vocabulary_structure(word)

    async def generate_batch_vocabulary_details(self, words: List[str]) -> List[Dict]:
        """
        Generate detail untuk batch kosakata secara sekuensial dengan throttling.
        """
        if not words:
            return []

        self.logger.info(f"Memproses batch {len(words)} kata dengan throttling")
        
        processed_results = []
        for i, word in enumerate(words):
            try:
                self.logger.info(f"Memproses kata ke-{i+1}/{len(words)}: {word}")
                result = await self.generate_vocabulary_details(word)
                processed_results.append(result)
                
                # Delay yang lebih lama antara permintaan untuk menghindari rate limit
                if i < len(words) - 1:  # Skip delay setelah item terakhir
                    delay = random.uniform(1, 2)  # Variasi delay 1-2 detik
                    self.logger.info(f"Menunggu {delay:.2f} detik sebelum permintaan berikutnya")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Error processing word '{word}': {str(e)}")
                processed_results.append(self._default_vocabulary_structure(word))
        
        return processed_results

    async def extract_vocabulary_from_transcript(self, transcript: str, max_vocab=5) -> List[Dict]:
        """
        Mengekstrak kosakata dari transkrip bahasa Jepang menggunakan OpenAI API.
        
        Args:
            transcript (str): Teks transkrip bahasa Jepang
            max_vocab (int): Jumlah maksimum kosakata yang akan diekstrak
                
        Returns:
            List[Dict]: List dictionary berisi detail kosakata
        """
        self.logger.info(f"Mulai ekstraksi kosakata (max: {max_vocab}) dari transkrip dengan OpenAI API")
        
        # Potong transkrip jika terlalu panjang
        max_transcript_length = 4000
        if len(transcript) > max_transcript_length:
            truncated_transcript = transcript[:max_transcript_length] + "..."
            self.logger.info(f"Transkrip dipotong dari {len(transcript)} menjadi {len(truncated_transcript)} karakter")
        else:
            truncated_transcript = transcript
        
        system_prompt = """
        Kamu adalah asisten bahasa Jepang yang ahli. Tugasmu adalah mengekstrak kosakata penting dari transkrip bahasa Jepang
        dan menyajikannya dalam format yang sesuai untuk flashcard. Berikan output hanya dalam format JSON yang diminta.
        """
        
        user_prompt = f"""
        Analisis transkrip bahasa Jepang berikut dan ekstrak {max_vocab} kosakata penting yang cocok untuk flashcard.
        
        Transkrip:
        {truncated_transcript}
        
        Untuk setiap kosakata, berikan informasi dalam format JSON array berikut:
        [
            {{
                "kanji": "kata dalam bentuk kanji (jika ada)",
                "kana": "cara baca dalam hiragana",
                "romaji": "penulisan dalam romaji",
                "arti": "arti dalam bahasa Indonesia",
                "level": "perkiraan level JLPT (N5, N4, N3, N2, N1)",
                "kategori": "kategori kata (Kata Kerja, Kata Benda, dll)",
                "contoh_kalimat": [
                    {{
                        "kalimat": "contoh kalimat dalam bahasa Jepang",
                        "kana": "cara baca contoh kalimat",
                        "arti": "arti contoh kalimat dalam bahasa Indonesia"
                    }}
                ]
            }}
        ]
        
        PENTING: 
        - Berikan HANYA array JSON yang valid
        - Setiap kosakata harus memiliki minimal 1 contoh kalimat
        - Tidak ada teks tambahan di luar JSON
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self._call_openai_with_retry(
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Membersihkan output dari markdown code block jika ada
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Cari array JSON dalam response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = content[json_start:json_end]
                vocabulary_items = json.loads(json_text)
            else:
                # Jika tidak ditemukan format array, coba parse seluruh teks
                vocabulary_items = json.loads(content)
            
            # Pastikan hasilnya adalah list
            if not isinstance(vocabulary_items, list):
                self.logger.warning("Response bukan dalam format array, mengonversi...")
                vocabulary_items = [vocabulary_items] if vocabulary_items else []
            
            self.logger.info(f"Berhasil mengekstrak {len(vocabulary_items)} kosakata dari transkrip")
            return vocabulary_items
        
        except json.JSONDecodeError as json_e:
            self.logger.error(f"JSONDecodeError dalam ekstraksi kosakata dari transkrip: {json_e}")
            self.logger.error("Pastikan output dari OpenAI API adalah JSON array yang valid")
            return []
            
        except Exception as e:
            self.logger.error(f"Error dalam ekstraksi kosakata dari transkrip: {str(e)}")
            return []
