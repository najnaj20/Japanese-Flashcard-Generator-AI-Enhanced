import google.generativeai as genai
import logging
from typing import List, Dict
import json

class AIHelper:
    def __init__(self, api_key: str):
        """
        Inisialisasi AI Helper dengan Gemini API
        
        Args:
            api_key (str): API key untuk Google Gemini
        """
        self.logger = self._setup_logger()
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.logger.info("Gemini AI initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini AI: {str(e)}")
            raise

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

    async def generate_vocabulary_details(self, word: str) -> Dict:
        """
        Generate detail kosakata menggunakan Gemini AI
        
        Args:
            word (str): Kata dalam bahasa Jepang
            
        Returns:
            Dict: Dictionary berisi detail kosakata
        """
        try:
            prompt = f"""
            Berikan informasi detail tentang kata bahasa Jepang "{word}" dalam format JSON dengan struktur berikut:
            {{
                "kanji": "kanji dari kata (jika ada)",
                "kana": "cara baca dalam hiragana",
                "romaji": "cara baca dalam romaji",
                "arti": "arti dalam bahasa Indonesia",
                "contoh_kalimat": [
                    {{
                        "kalimat": "contoh kalimat dalam bahasa Jepang",
                        "kana": "cara baca kalimat dalam hiragana",
                        "arti": "arti kalimat dalam bahasa Indonesia"
                    }}
                ],
                "level": "tingkat JLPT (N5-N1)",
                "kategori": "kategori kata (kata kerja, kata sifat, kata benda, dll)"
            }}
            
            Pastikan output dalam format JSON yang valid dan berikan minimal 2 contoh kalimat.
            """

            response = await self.model.generate_content(prompt)
            result = json.loads(response.text)
            self.logger.info(f"Successfully generated details for word: {word}")
            return result

        except Exception as e:
            self.logger.error(f"Error generating vocabulary details for {word}: {str(e)}")
            return {
                "kanji": word,
                "kana": word,
                "romaji": "",
                "arti": "Error generating details",
                "contoh_kalimat": [],
                "level": "Unknown",
                "kategori": "Unknown"
            }

    async def generate_batch_vocabulary_details(self, words: List[str]) -> List[Dict]:
        """
        Generate detail untuk batch kosakata
        
        Args:
            words (List[str]): List kata-kata Jepang
            
        Returns:
            List[Dict]: List dictionary berisi detail kosakata
        """
        results = []
        for word in words:
            try:
                detail = await self.generate_vocabulary_details(word)
                results.append(detail)
            except Exception as e:
                self.logger.error(f"Error processing word {word}: {str(e)}")
                results.append({
                    "kanji": word,
                    "kana": word,
                    "romaji": "",
                    "arti": "Error generating details",
                    "contoh_kalimat": [],
                    "level": "Unknown",
                    "kategori": "Unknown"
                })
        return results
