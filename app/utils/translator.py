import openai
import time
import logging
import os
from typing import Optional

class JapaneseTranslator:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI Japanese Translator
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        try:
            # Coba ambil API key dari environment variable jika tidak disediakan
            if api_key is None:
                api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                raise ValueError("API Key untuk OpenAI tidak ditemukan. Set OPENAI_API_KEY environment variable.")
            
            # Initialize OpenAI client
            self.client = openai.OpenAI(api_key=api_key)
            
            # Test connection
            self._test_connection()
            
            logging.info("OpenAI Translator berhasil diinisialisasi")
            
        except Exception as e:
            logging.error(f"Gagal inisialisasi OpenAI Translator: {e}")
            raise

    def _test_connection(self):
        """Test OpenAI API connection"""
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1
            )
            logging.info("OpenAI API connection successful")
        except Exception as e:
            logging.error(f"OpenAI API connection failed: {e}")
            raise

    def translate_text(self, text: str, src: str = 'ja', dest: str = 'id', model: str = "gpt-3.5-turbo") -> str:
        """
        Translate text using OpenAI GPT
        
        Args:
            text: Text to translate
            src: Source language code (default: 'ja' for Japanese)
            dest: Destination language code (default: 'id' for Indonesian)
            model: OpenAI model to use (default: gpt-3.5-turbo)
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return ""
            
        try:
            # Language mapping
            lang_map = {
                'ja': 'Japanese',
                'id': 'Indonesian', 
                'en': 'English',
                'ko': 'Korean',
                'zh': 'Chinese'
            }
            
            src_lang = lang_map.get(src, src)
            dest_lang = lang_map.get(dest, dest)
            
            # Create translation prompt
            prompt = f"""
            Translate the following text from {src_lang} to {dest_lang}.
            
            Text to translate: {text}
            
            Instructions:
            - Provide only the translation without any additional explanation
            - Maintain the original meaning and context
            - Use natural and fluent {dest_lang}
            - If the text contains Japanese particles or grammar, translate them appropriately
            
            Translation:
            """
            
            # Make API request
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a professional translator specializing in {src_lang} to {dest_lang} translation. Provide accurate, natural translations."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for more consistent translations
                top_p=1.0
            )
            
            translation = response.choices[0].message.content.strip()
            
            # Clean up the response (remove any unwanted prefixes)
            if translation.startswith("Translation:"):
                translation = translation.replace("Translation:", "").strip()
            
            logging.info(f"Translation successful: {text[:50]}... -> {translation[:50]}...")
            return translation
            
        except openai.RateLimitError:
            logging.error("OpenAI API rate limit exceeded")
            time.sleep(1)  # Wait before retry
            return self._fallback_translation(text, src, dest)
            
        except openai.APIError as e:
            logging.error(f"OpenAI API error: {e}")
            return self._fallback_translation(text, src, dest)
            
        except Exception as e:
            logging.error(f"Gagal menerjemahkan dengan OpenAI: {e}")
            return self._fallback_translation(text, src, dest)

    def _fallback_translation(self, text: str, src: str = 'ja', dest: str = 'id') -> str:
        """
        Fallback translation using deep-translator (Google Translate)
        
        Args:
            text: Text to translate
            src: Source language
            dest: Destination language
            
        Returns:
            Translated text or original text if translation fails
        """
        try:
            from deep_translator import GoogleTranslator
            
            # Convert language codes for Google Translate
            google_src = 'ja' if src == 'ja' else 'auto'
            google_dest = 'id' if dest == 'id' else 'en'
            
            translator = GoogleTranslator(source=google_src, target=google_dest)
            result = translator.translate(text)
            
            logging.info(f"Fallback translation successful: {text[:30]}...")
            return result if result else text
            
        except Exception as e:
            logging.error(f"Fallback translation failed: {e}")
            return text

    def translate_japanese_to_indonesian(self, japanese_text: str) -> str:
        """
        Convenience method to translate Japanese to Indonesian
        
        Args:
            japanese_text: Japanese text to translate
            
        Returns:
            Indonesian translation
        """
        return self.translate_text(japanese_text, src='ja', dest='id')

    def translate_to_english(self, text: str, src: str = 'ja') -> str:
        """
        Convenience method to translate to English
        
        Args:
            text: Text to translate
            src: Source language (default: Japanese)
            
        Returns:
            English translation
        """
        return self.translate_text(text, src=src, dest='en')

    def batch_translate(self, texts: list, src: str = 'ja', dest: str = 'id', delay: float = 0.5) -> list:
        """
        Translate multiple texts with rate limiting
        
        Args:
            texts: List of texts to translate
            src: Source language
            dest: Destination language
            delay: Delay between requests (seconds)
            
        Returns:
            List of translated texts
        """
        translations = []
        
        for i, text in enumerate(texts):
            try:
                translation = self.translate_text(text, src, dest)
                translations.append(translation)
                
                # Add delay to avoid rate limiting
                if i < len(texts) - 1:  # Don't delay after last item
                    time.sleep(delay)
                    
            except Exception as e:
                logging.error(f"Batch translation error for item {i}: {e}")
                translations.append(text)  # Keep original text if translation fails
                
        return translations

    def get_supported_models(self) -> list:
        """
        Get list of supported OpenAI models
        
        Returns:
            List of model names
        """
        return [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-turbo-preview"
        ]


# Global instance untuk backward compatibility
def create_translator(api_key: Optional[str] = None) -> JapaneseTranslator:
    """
    Factory function to create translator instance
    
    Args:
        api_key: OpenAI API key
        
    Returns:
        JapaneseTranslator instance
    """
    return JapaneseTranslator(api_key=api_key)


# Example usage
if __name__ == "__main__":
    # Test the translator
    try:
        translator = JapaneseTranslator()
        
        # Test single translation
        japanese_text = "こんにちは、元気ですか？"
        translation = translator.translate_japanese_to_indonesian(japanese_text)
        print(f"Japanese: {japanese_text}")
        print(f"Indonesian: {translation}")
        
        # Test batch translation
        texts = ["おはよう", "ありがとう", "さようなら"]
        translations = translator.batch_translate(texts)
        
        for jp, id_text in zip(texts, translations):
            print(f"{jp} -> {id_text}")
            
    except Exception as e:
        print(f"Error: {e}")
