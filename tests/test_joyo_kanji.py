import unittest
import os
import sys

# Adjust path to import JOYO_KANJI from the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/extract_serif')))
from joyo_kanji import JOYO_KANJI

# Helper functions that would ideally be in joyo_kanji.py, defined here for testing JOYO_KANJI set.
def is_joyo_kanji(char_to_check):
    """
    Checks if a single character is a Joyo Kanji.
    """
    if not isinstance(char_to_check, str) or len(char_to_check) != 1:
        return False # Or raise ValueError, depending on desired strictness
    return char_to_check in JOYO_KANJI

def filter_joyo_kanji(text_to_filter):
    """
    Filters a string to keep only Joyo Kanji characters.
    """
    if not isinstance(text_to_filter, str):
        return "" # Or raise TypeError
    return "".join([char for char in text_to_filter if is_joyo_kanji(char)])

class TestJoyoKanji(unittest.TestCase):

    def test_joyo_kanji_set_loaded(self):
        self.assertIsNotNone(JOYO_KANJI)
        self.assertIsInstance(JOYO_KANJI, set)
        self.assertTrue(len(JOYO_KANJI) > 2000) # General check for substantial content

    def test_known_joyo_kanji_in_set(self):
        # Common Joyo Kanji
        self.assertIn("日", JOYO_KANJI)
        self.assertIn("月", JOYO_KANJI)
        self.assertIn("学", JOYO_KANJI)
        self.assertIn("生", JOYO_KANJI)
        self.assertIn("愛", JOYO_KANJI) # From the provided list start
        self.assertIn("和", JOYO_KANJI) # From the provided list end
        self.assertIn("腕", JOYO_KANJI) # From the provided list end

    def test_non_joyo_characters_not_in_set(self):
        # Non-Joyo Kanji (often specific to names, older forms, etc.)
        self.assertNotIn("﨑", JOYO_KANJI) # Common name variant
        self.assertNotIn("煉", JOYO_KANJI) # Older kanji, sometimes seen
        self.assertNotIn("Ç", JOYO_KANJI)  # Non-Japanese character
        
        # Hiragana
        self.assertNotIn("あ", JOYO_KANJI)
        self.assertNotIn("い", JOYO_KANJI)
        
        # Katakana
        self.assertNotIn("ア", JOYO_KANJI)
        self.assertNotIn("イ", JOYO_KANJI)
        
        # Punctuation
        self.assertNotIn("。", JOYO_KANJI)
        self.assertNotIn("、", JOYO_KANJI)
        self.assertNotIn("「", JOYO_KANJI)
        
        # Alphanumeric
        self.assertNotIn("A", JOYO_KANJI)
        self.assertNotIn("1", JOYO_KANJI)
        
        # Symbols
        self.assertNotIn("¥", JOYO_KANJI)

    def test_is_joyo_kanji_function(self):
        self.assertTrue(is_joyo_kanji("学"))
        self.assertTrue(is_joyo_kanji("食"))
        self.assertFalse(is_joyo_kanji("﨑")) # Non-Joyo
        self.assertFalse(is_joyo_kanji("あ")) # Hiragana
        self.assertFalse(is_joyo_kanji("ア")) # Katakana
        self.assertFalse(is_joyo_kanji("!"))  # Punctuation
        self.assertFalse(is_joyo_kanji("B"))  # Latin alphabet
        self.assertFalse(is_joyo_kanji("7"))  # Digit
        self.assertFalse(is_joyo_kanji(""))   # Empty string
        self.assertFalse(is_joyo_kanji("日本")) # Multi-character string
        self.assertFalse(is_joyo_kanji(123))   # Non-string input

    def test_filter_joyo_kanji_function(self):
        self.assertEqual(filter_joyo_kanji("学園生活"), "学園生活") # All Joyo
        self.assertEqual(filter_joyo_kanji("Hello 世界"), "世界")  # Mixed with non-Japanese
        self.assertEqual(filter_joyo_kanji("こんにちは、世界！"), "世界") # Mixed with kana and punctuation
        self.assertEqual(filter_joyo_kanji("煉獄さんは食べない"), "食") # Mixed with non-Joyo, kana
        self.assertEqual(filter_joyo_kanji("ひらがなとカタカナ"), "") # Only kana
        self.assertEqual(filter_joyo_kanji(""), "") # Empty string
        self.assertEqual(filter_joyo_kanji("123 ABC"), "") # Only alphanumeric
        self.assertEqual(filter_joyo_kanji("﨑田"), "田") # Non-Joyo and Joyo
        self.assertEqual(filter_joyo_kanji(None), "") # None input
        self.assertEqual(filter_joyo_kanji(12345), "") # Non-string input

if __name__ == '__main__':
    unittest.main()
