from typing import List, Dict, Optional, Union
import fugashi
from fugashi import UnidicNode
import jaconv
from langdetect import detect, DetectorFactory
import logging
import re
import unicodedata
import openai
import os
from dataclasses import dataclass
from enum import Enum

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class POSCategory(Enum):
    """Part-of-Speech categories for better type safety"""
    NOUN = "名詞"
    VERB = "動詞"
    ADJECTIVE = "形容詞"
    ADVERB = "副詞"
    PARTICLE = "助詞"
    AUXILIARY_VERB = "助動詞"
    CONJUNCTION = "接続詞"
    PREFIX = "接頭詞"
    SYMBOL = "記号"
    INTERJECTION = "感動詞"

@dataclass
class WordInfo:
    """Data class for word information"""
    surface: str
    reading: str
    romaji: str
    pos: str
    pos1: str
    pos2: str = ""
    pos3: str = ""
    pos4: str = ""
    normalized: str = ""
    definition: str = ""
    difficulty_level: str = ""
    frequency_score: int = 0

class VocabularyProcessor:
    def __init__(self, use_ai_enhancement: bool = True, openai_api_key: Optional[str] = None):
        """
        Initialize VocabularyProcessor with Fugashi tokenizer and optional AI enhancement
        
        Args:
            use_ai_enhancement: Whether to use OpenAI for enhanced word analysis
            openai_api_key: OpenAI API key for AI enhancement
        """
        try:
            self.tagger = fugashi.Tagger()
            self.use_ai_enhancement = use_ai_enhancement
            
            # Initialize OpenAI client if AI enhancement is enabled
            if self.use_ai_enhancement:
                api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
                if api_key:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    logger.info("OpenAI client initialized for vocabulary enhancement")
                else:
                    logger.warning("OpenAI API key not found. AI enhancement disabled.")
                    self.use_ai_enhancement = False
                    
        except Exception as e:
            logger.error(f"Failed to initialize VocabularyProcessor: {e}")
            raise

    def extract_vocabulary(self, 
                          text: str, 
                          min_length: int = 2, 
                          max_length: int = 10,
                          include_pos: Optional[List[str]] = None,
                          exclude_pos: Optional[List[str]] = None,
                          max_words: int = 100) -> List[Dict[str, str]]:
        """
        Extract unique Japanese vocabulary from text with advanced filtering
        
        Args:
            text: Input text to extract vocabulary from
            min_length: Minimum word length to include
            max_length: Maximum word length to include
            include_pos: Specific POS to include (overrides default exclusions)
            exclude_pos: Additional POS to exclude
            max_words: Maximum number of words to return
        
        Returns:
            List of vocabulary words with details
        """
        try:
            if not text or not isinstance(text, str):
                logger.warning("Invalid input text received for vocabulary extraction.")
                return []

            # Clean and preprocess text
            text = self._preprocess_text(text)
            
            # Language detection with fallback
            if not self._is_likely_japanese(text):
                logger.warning("Input text may not be Japanese")
                # Continue processing anyway, but log the warning

            # Set up POS filtering
            default_exclude_pos = [
                POSCategory.PARTICLE.value,
                POSCategory.SYMBOL.value,
                POSCategory.AUXILIARY_VERB.value,
                POSCategory.CONJUNCTION.value,
                POSCategory.PREFIX.value
            ]
            
            if exclude_pos:
                current_exclude_pos = list(set(default_exclude_pos + exclude_pos))
            else:
                current_exclude_pos = default_exclude_pos
                
            if include_pos:
                # If specific POS are requested, only exclude symbols and particles
                current_exclude_pos = [POSCategory.SYMBOL.value]

            vocabulary = []
            seen_words = set()
            word_frequency = {}

            # First pass: collect all words and their frequencies
            for word_token in self.tagger(text):
                surface = word_token.surface
                if surface in word_frequency:
                    word_frequency[surface] += 1
                else:
                    word_frequency[surface] = 1

            # Second pass: extract vocabulary with filtering
            for word_token in self.tagger(text):
                surface = word_token.surface
                
                if (self._is_valid_word(word_token, current_exclude_pos, include_pos) and
                    min_length <= len(surface) <= max_length and 
                    surface not in seen_words and 
                    self._is_japanese_word(surface)):
                    
                    word_details = self._get_enhanced_word_details(word_token, word_frequency.get(surface, 1))
                    
                    if word_details:
                        vocabulary.append(word_details)
                        seen_words.add(surface)
                        
                        # Stop if we've reached the maximum number of words
                        if len(vocabulary) >= max_words:
                            break

            # Sort by frequency and difficulty for better learning order
            vocabulary = self._sort_vocabulary(vocabulary)
            
            return vocabulary

        except Exception as e:
            logger.error(f"Error in vocabulary extraction: {e}", exc_info=True)
            return []

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text by cleaning and normalizing"""
        try:
            # Remove excessive whitespace and normalize
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Normalize Unicode
            text = unicodedata.normalize('NFKC', text)
            
            # Remove certain symbols that might interfere with parsing
            text = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3000-\u303F]', '', text)
            
            return text
        except Exception as e:
            logger.error(f"Error preprocessing text: {e}")
            return text

    def _is_likely_japanese(self, text: str) -> bool:
        """Check if text is likely Japanese with better error handling"""
        try:
            if len(text.strip()) < 5:
                logger.debug("Text too short for reliable language detection")
                return True  # Assume Japanese for short text
                
            detected_lang = detect(text)
            return detected_lang == 'ja'
            
        except Exception as e:
            logger.debug(f"Language detection failed: {e}. Assuming Japanese.")
            return True  # Fallback to assuming Japanese

    def _is_valid_word(self, 
                      word_token: UnidicNode, 
                      exclude_pos: List[str],
                      include_pos: Optional[List[str]] = None) -> bool:
        """
        Check if word is valid for vocabulary extraction with enhanced logic
        """
        try:
            # Get POS information
            pos1 = getattr(word_token.feature, 'pos1', '')
            pos2 = getattr(word_token.feature, 'pos2', '')
            surface = word_token.surface
            
            # If specific POS are requested, check inclusion first
            if include_pos:
                if pos1 not in include_pos:
                    return False
            
            # Check exclusions
            if pos1 in exclude_pos:
                return False
                
            # Additional filtering rules
            if (pos1.startswith('記号') or  # Exclude symbols
                len(surface) == 1 and pos1 == '助詞' or  # Single character particles
                surface.isdigit() or  # Pure numbers
                re.match(r'^[a-zA-Z]+$', surface)):  # Pure English words
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating word: {e}")
            return False

    def _is_japanese_word(self, word: str) -> bool:
        """Check if the word contains Japanese characters"""
        if not word:
            return False
            
        japanese_ranges = [
            (0x3040, 0x309F),   # Hiragana
            (0x30A0, 0x30FF),   # Katakana
            (0x4E00, 0x9FFF),   # Kanji (CJK Unified Ideographs)
        ]
        
        # At least one character must be Japanese
        return any(
            any(start <= ord(char) <= end for start, end in japanese_ranges)
            for char in word
        )

    def _get_enhanced_word_details(self, word_token: UnidicNode, frequency: int = 1) -> Dict[str, str]:
        """Get comprehensive details about a word with AI enhancement"""
        try:
            surface = word_token.surface
            feature = word_token.feature
            
            # Basic word information
            word_info = {
                'surface': surface,
                'reading': self._normalize_reading(getattr(feature, 'kana', '') or surface),
                'romaji': self._to_romaji(getattr(feature, 'kana', '') or surface),
                'pos': getattr(feature, 'pos1', ''),
                'pos1': getattr(feature, 'pos1', ''),
                'pos2': getattr(feature, 'pos2', ''),
                'pos3': getattr(feature, 'pos3', ''),
                'pos4': getattr(feature, 'pos4', ''),
                'normalized': self._normalize_text(surface),
                'frequency_score': frequency
            }
            
            # Add AI enhancement if enabled
            if self.use_ai_enhancement:
                ai_info = self._get_ai_word_analysis(surface)
                word_info.update(ai_info)
            
            return word_info
            
        except Exception as e:
            logger.error(f"Error getting word details for '{word_token.surface}': {e}")
            return {}

    def _get_ai_word_analysis(self, word: str) -> Dict[str, str]:
        """Get AI-powered word analysis including definition and difficulty"""
        try:
            if not self.use_ai_enhancement or not hasattr(self, 'openai_client'):
                return {}
                
            prompt = f"""
Analyze this Japanese word: {word}

Provide:
1. English definition (brief, 1-2 sentences)
2. Difficulty level (Beginner/Intermediate/Advanced)
3. Usage context (Formal/Informal/Both)

Format your response as:
Definition: [definition]
Difficulty: [level]
Context: [usage context]
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Japanese language expert providing concise word analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200,
                timeout=15
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse the response
            ai_info = {}
            for line in content.split('\n'):
                if line.startswith('Definition:'):
                    ai_info['definition'] = line.replace('Definition:', '').strip()
                elif line.startswith('Difficulty:'):
                    ai_info['difficulty_level'] = line.replace('Difficulty:', '').strip()
                elif line.startswith('Context:'):
                    ai_info['usage_context'] = line.replace('Context:', '').strip()
            
            return ai_info
            
        except Exception as e:
            logger.debug(f"AI analysis failed for word '{word}': {e}")
            return {}

    def _normalize_reading(self, reading: str) -> str:
        """Normalize reading (convert to hiragana)"""
        try:
            if not reading:
                return ''
            return jaconv.kata2hira(reading)
        except Exception as e:
            logger.debug(f"Error normalizing reading '{reading}': {e}")
            return reading or ''

    def _to_romaji(self, text: str) -> str:
        """Convert Japanese text to romaji"""
        try:
            if not text:
                return ''
            # Convert to hiragana first for better romaji conversion
            hiragana_text = jaconv.kata2hira(text)
            return jaconv.hiragana2romaji(hiragana_text)
        except Exception as e:
            logger.debug(f"Error converting to romaji '{text}': {e}")
            return ''

    def _normalize_text(self, text: str) -> str:
        """Normalize text using Unicode normalization"""
        try:
            if not text:
                return ''
            return unicodedata.normalize('NFKC', text)
        except Exception as e:
            logger.debug(f"Error normalizing text '{text}': {e}")
            return text or ''

    def _sort_vocabulary(self, vocabulary: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Sort vocabulary by frequency and difficulty for optimal learning order"""
        try:
            def sort_key(word):
                # Priority: frequency (higher first), then difficulty (beginner first)
                frequency = word.get('frequency_score', 1)
                difficulty = word.get('difficulty_level', 'Intermediate')
                
                difficulty_order = {'Beginner': 1, 'Intermediate': 2, 'Advanced': 3}
                difficulty_score = difficulty_order.get(difficulty, 2)
                
                # Higher frequency and lower difficulty = lower sort value (appears first)
                return (-frequency, difficulty_score)
            
            return sorted(vocabulary, key=sort_key)
            
        except Exception as e:
            logger.error(f"Error sorting vocabulary: {e}")
            return vocabulary

    def filter_vocabulary(self, 
                         vocabulary: List[Dict[str, str]], 
                         pos_filter: Optional[List[str]] = None,
                         min_length: Optional[int] = None,
                         max_length: Optional[int] = None,
                         difficulty_filter: Optional[List[str]] = None,
                         min_frequency: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Advanced filtering of vocabulary list with additional criteria
        """
        try:
            filtered_vocab = vocabulary.copy()
            
            if pos_filter:
                filtered_vocab = [
                    word for word in filtered_vocab 
                    if word.get('pos') in pos_filter
                ]
            
            if min_length is not None:
                filtered_vocab = [
                    word for word in filtered_vocab 
                    if len(word.get('surface', '')) >= min_length
                ]
            
            if max_length is not None:
                filtered_vocab = [
                    word for word in filtered_vocab 
                    if len(word.get('surface', '')) <= max_length
                ]
                
            if difficulty_filter:
                filtered_vocab = [
                    word for word in filtered_vocab 
                    if word.get('difficulty_level') in difficulty_filter
                ]
                
            if min_frequency is not None:
                filtered_vocab = [
                    word for word in filtered_vocab 
                    if word.get('frequency_score', 0) >= min_frequency
                ]
            
            return filtered_vocab
            
        except Exception as e:
            logger.error(f"Error filtering vocabulary: {e}")
            return vocabulary

    def get_vocabulary_stats(self, vocabulary: List[Dict[str, str]]) -> Dict[str, Union[int, Dict[str, int]]]:
        """Get statistics about the vocabulary list"""
        try:
            if not vocabulary:
                return {}
                
            stats = {
                'total_words': len(vocabulary),
                'pos_distribution': {},
                'difficulty_distribution': {},
                'length_distribution': {},
                'average_frequency': 0
            }
            
            # Calculate distributions
            for word in vocabulary:
                # POS distribution
                pos = word.get('pos', 'Unknown')
                stats['pos_distribution'][pos] = stats['pos_distribution'].get(pos, 0) + 1
                
                # Difficulty distribution
                difficulty = word.get('difficulty_level', 'Unknown')
                stats['difficulty_distribution'][difficulty] = stats['difficulty_distribution'].get(difficulty, 0) + 1
                
                # Length distribution
                length = len(word.get('surface', ''))
                length_key = f"{length} chars"
                stats['length_distribution'][length_key] = stats['length_distribution'].get(length_key, 0) + 1
            
            # Average frequency
            frequencies = [word.get('frequency_score', 0) for word in vocabulary]
            stats['average_frequency'] = sum(frequencies) / len(frequencies) if frequencies else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating vocabulary stats: {e}")
            return {}

    def export_vocabulary(self, vocabulary: List[Dict[str, str]], format: str = 'json') -> str:
        """Export vocabulary to different formats"""
        try:
            if format.lower() == 'json':
                import json
                return json.dumps(vocabulary, ensure_ascii=False, indent=2)
                
            elif format.lower() == 'csv':
                import csv
                import io
                
                if not vocabulary:
                    return ""
                    
                output = io.StringIO()
                fieldnames = vocabulary[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(vocabulary)
                return output.getvalue()
                
            elif format.lower() == 'tsv':
                import csv
                import io
                
                if not vocabulary:
                    return ""
                    
                output = io.StringIO()
                fieldnames = vocabulary[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter='\t')
                writer.writeheader()
                writer.writerows(vocabulary)
                return output.getvalue()
                
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting vocabulary: {e}")
            return ""

# Utility functions
def create_vocabulary_processor(use_ai: bool = True, api_key: Optional[str] = None) -> VocabularyProcessor:
    """Create a VocabularyProcessor instance"""
    return VocabularyProcessor(use_ai_enhancement=use_ai, openai_api_key=api_key)

def quick_extract(text: str, max_words: int = 20) -> List[Dict[str, str]]:
    """Quick vocabulary extraction for simple use cases"""
    processor = VocabularyProcessor(use_ai_enhancement=False)
    return processor.extract_vocabulary(text, max_words=max_words)

# Test function
def test_vocabulary_processor():
    """Test the vocabulary processor functionality"""
    try:
        processor = VocabularyProcessor(use_ai_enhancement=True)
        
        test_text = "今日は良い天気ですね。桜の花が綺麗に咲いています。"
        
        print("=== Testing Vocabulary Processor ===")
        vocabulary = processor.extract_vocabulary(test_text, max_words=10)
        
        for word in vocabulary:
            print(f"Word: {word.get('surface')}")
            print(f"  Reading: {word.get('reading')}")
            print(f"  Romaji: {word.get('romaji')}")
            print(f"  POS: {word.get('pos')}")
            if word.get('definition'):
                print(f"  Definition: {word.get('definition')}")
            print()
        
        # Test statistics
        stats = processor.get_vocabulary_stats(vocabulary)
        print("=== Vocabulary Statistics ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_vocabulary_processor()
