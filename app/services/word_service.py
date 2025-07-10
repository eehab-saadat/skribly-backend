import json
import random
import os
from typing import List, Dict

class WordService:
    def __init__(self):
        self.words_cache: Dict[str, List[str]] = {}
        self.app = None
        self._load_words()
    
    def init_app(self, app):
        """Initialize the word service with Flask app"""
        self.app = app
        print("📚 Word service initialized")
    
    def _load_words(self):
        """Load words from JSON files"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            words_dir = os.path.join(current_dir, '..', 'static', 'words')
            
            difficulties = ['easy', 'medium', 'hard']
            
            for difficulty in difficulties:
                file_path = os.path.join(words_dir, f'{difficulty}.json')
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.words_cache[difficulty] = json.load(f)
                    print(f"📖 Loaded {len(self.words_cache[difficulty])} {difficulty} words")
                else:
                    print(f"⚠️ Word file not found: {file_path}")
                    # Fallback words
                    self.words_cache[difficulty] = self._get_fallback_words(difficulty)
                    
        except Exception as e:
            print(f"❌ Error loading words: {e}")
            self._load_fallback_words()
    
    def _get_fallback_words(self, difficulty: str) -> List[str]:
        """Get fallback words if JSON files are not available"""
        fallback_words = {
            'easy': [
                'cat', 'dog', 'fish', 'bird', 'car', 'tree', 'house', 'sun', 'moon', 'star',
                'ball', 'book', 'pen', 'cup', 'hat', 'cake', 'apple', 'egg', 'bee', 'key'
            ],
            'medium': [
                'elephant', 'giraffe', 'butterfly', 'dinosaur', 'rainbow', 'mountain', 'guitar',
                'piano', 'bicycle', 'airplane', 'sandwich', 'pizza', 'teacher', 'doctor', 'castle'
            ],
            'hard': [
                'cryptocurrency', 'photosynthesis', 'metamorphosis', 'constellation', 'entrepreneur',
                'procrastination', 'refrigerator', 'democracy', 'philosophy', 'magnificent'
            ]
        }
        return fallback_words.get(difficulty, fallback_words['easy'])
    
    def _load_fallback_words(self):
        """Load fallback words if all else fails"""
        self.words_cache = {
            'easy': self._get_fallback_words('easy'),
            'medium': self._get_fallback_words('medium'),
            'hard': self._get_fallback_words('hard')
        }
        print("🔄 Loaded fallback words")
    
    def get_random_words(self, difficulty: str = 'medium', count: int = 3) -> List[str]:
        """Get random words for selection"""
        if difficulty not in self.words_cache:
            difficulty = 'medium'
        
        available_words = self.words_cache[difficulty]
        if len(available_words) < count:
            return available_words[:]
        
        return random.sample(available_words, count)
    
    def get_random_word(self, difficulty: str = 'medium') -> str:
        """Get a single random word"""
        words = self.get_random_words(difficulty, 1)
        return words[0] if words else 'drawing'
    
    def validate_word(self, word: str, difficulty: str = 'medium') -> bool:
        """Check if a word exists in the given difficulty"""
        if difficulty not in self.words_cache:
            return False
        return word.lower() in [w.lower() for w in self.words_cache[difficulty]]
    
    def get_word_hint(self, word, revealed_positions=None):
        """
        Generate a word hint with specific positions revealed
        Args:
            word: The word to create a hint for
            revealed_positions: List of indices to reveal (0-based) or integer for backward compatibility
        Returns:
            String with revealed letters and underscores
        """
        if not word:
            return ""
        
        if revealed_positions is None:
            revealed_positions = []
        elif isinstance(revealed_positions, int):
            # Backward compatibility: if an integer is passed, reveal that many random letters
            import random
            letter_positions = [i for i, char in enumerate(word) if char != ' ']
            if letter_positions:
                num_to_reveal = min(revealed_positions, len(letter_positions))
                revealed_positions = random.sample(letter_positions, num_to_reveal)
            else:
                revealed_positions = []
        
        hint = []
        for i, char in enumerate(word.lower()):
            if char == ' ':
                hint.append(' ')
            elif i in revealed_positions:
                hint.append(char.upper())
            else:
                hint.append('_')
        
        return ' '.join(hint)
    
    def get_progressive_hint(self, word, elapsed_seconds):
        """
        Generate progressive hints for Skribbl.io style gameplay
        Reveals up to 3 letters every 10 seconds, starting after 10 seconds
        
        Args:
            word: The word to create hints for
            elapsed_seconds: How many seconds have passed since drawing started
        Returns:
            String hint with revealed letters
        """
        if not word or elapsed_seconds < 10:
            return '_' * len(word.replace(' ', ''))
        
        # Calculate how many letters to reveal (max 3, one every 10 seconds after initial 10s)
        letters_to_reveal = min(3, (elapsed_seconds - 10) // 10 + 1)
        
        # Get letter positions (excluding spaces)
        letter_positions = [i for i, char in enumerate(word) if char != ' ']
        
        if not letter_positions:
            return word
        
        # Strategically reveal letters (first, last, then middle)
        revealed_positions = []
        if letters_to_reveal >= 1 and len(letter_positions) >= 1:
            revealed_positions.append(letter_positions[0])  # First letter
        if letters_to_reveal >= 2 and len(letter_positions) >= 2:
            revealed_positions.append(letter_positions[-1])  # Last letter  
        if letters_to_reveal >= 3 and len(letter_positions) >= 3:
            middle_pos = letter_positions[len(letter_positions) // 2]
            revealed_positions.append(middle_pos)  # Middle letter
        
        return self.get_word_hint(word, revealed_positions)
    
    def get_similar_words(self, word: str, difficulty: str = 'medium', count: int = 5) -> List[str]:
        """Get words similar in length or starting letter"""
        if difficulty not in self.words_cache:
            return []
        
        available_words = self.words_cache[difficulty]
        word_len = len(word)
        word_start = word[0].lower() if word else ''
        
        # Find words with similar length or starting letter
        similar = []
        for w in available_words:
            if w.lower() != word.lower():
                if (len(w) == word_len or 
                    (w and w[0].lower() == word_start)):
                    similar.append(w)
        
        return random.sample(similar, min(count, len(similar)))
    
    def get_words_by_category(self, category: str, difficulty: str = 'medium') -> List[str]:
        """Get words by category (for future enhancement)"""
        # This is a placeholder for future category-based word selection
        # For now, just return random words
        return self.get_random_words(difficulty, 10)
    
    def get_word_stats(self) -> Dict[str, int]:
        """Get statistics about loaded words"""
        return {
            difficulty: len(words) 
            for difficulty, words in self.words_cache.items()
        }

# Global instance
word_service = WordService() 