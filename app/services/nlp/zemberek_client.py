"""
Zemberek Turkish NLP Client

Handles Turkish morphological analysis, normalization, and stemming.
Uses fallback rules when Zemberek library is not available.
"""
from typing import Dict, List, Optional


class ZemberekClient:
    """
    Turkish NLP processor with Zemberek-compatible fallback

    Provides:
    - Morphological analysis
    - Root word extraction
    - Turkish text normalization
    - Character conversion (Turkish-specific)
    """

    def __init__(self):
        self._initialized = False
        self._load_zemberek()

    def _load_zemberek(self):
        """
        Attempt to load Zemberek library

        Note: Zemberek is a Java library. For production, use py4j or jnius.
        For now, using fallback implementation.
        """
        try:
            # TODO: Implement actual Zemberek integration via py4j
            # from py4j.java_gateway import JavaGateway
            # self.gateway = JavaGateway()
            # self.morphology = self.gateway.entry_point.getTurkishMorphology()
            self._initialized = False
        except Exception as e:
            print(f"⚠️ Zemberek not available, using fallback: {e}")
            self._initialized = False

    def analyze(self, word: str) -> Dict:
        """
        Perform morphological analysis on a Turkish word

        Args:
            word: Turkish word to analyze

        Returns:
            Dict with keys: word, root, pos, suffixes, is_valid
        """
        if self._initialized:
            return self._zemberek_analyze(word)
        else:
            return self._fallback_analyze(word)

    def get_root(self, word: str) -> str:
        """
        Extract root form of a Turkish word

        Args:
            word: Turkish word

        Returns:
            Root form (kök)
        """
        result = self.analyze(word)
        return result.get('root', word.lower())

    def normalize(self, text: str) -> str:
        """
        Normalize Turkish text (lowercase, handle İ/ı correctly)

        Turkish has special case conversion rules:
        - I -> ı (not i)
        - İ -> i (not I)
        """
        # Turkish-aware lowercase
        replacements = {
            'I': 'ı',
            'İ': 'i',
            'Ğ': 'ğ',
            'Ü': 'ü',
            'Ş': 'ş',
            'Ö': 'ö',
            'Ç': 'ç'
        }

        for upper, lower in replacements.items():
            text = text.replace(upper, lower)

        return text.lower()

    def _zemberek_analyze(self, word: str) -> Dict:
        """Actual Zemberek analysis (when library is available)"""
        # TODO: Implement when Zemberek is integrated
        pass

    def _fallback_analyze(self, word: str) -> Dict:
        """
        Fallback morphological analysis using rule-based approach

        This is a simplified implementation. For production, integrate actual Zemberek.
        """
        # Common Turkish suffixes (in order of application)
        common_suffixes = [
            # Plural
            'lar', 'ler',
            # Possessive
            'ım', 'im', 'um', 'üm',
            'ın', 'in', 'un', 'ün',
            # Case markers
            'da', 'de', 'ta', 'te',
            'dan', 'den', 'tan', 'ten',
            'ı', 'i', 'u', 'ü',
            'a', 'e',
            # Derivational
            'lık', 'lik', 'luk', 'lük',
            'cı', 'ci', 'cu', 'cü',
            'sız', 'siz', 'suz', 'süz',
        ]

        word_lower = self.normalize(word)
        root = word_lower
        found_suffixes = []

        # Try to strip suffixes
        for suffix in sorted(common_suffixes, key=len, reverse=True):
            if root.endswith(suffix) and len(root) > len(suffix) + 2:
                # Keep at least 3 characters in root
                potential_root = root[:-len(suffix)]
                if len(potential_root) >= 3:
                    found_suffixes.insert(0, suffix)
                    root = potential_root
                    break  # Only strip one suffix in this simple version

        return {
            'word': word,
            'root': root,
            'pos': 'Unknown',  # Would be determined by Zemberek
            'suffixes': found_suffixes,
            'is_valid': True,
            'normalized': word_lower
        }

    def get_stem_variants(self, word: str) -> List[str]:
        """
        Get potential stem variants for search expansion

        Returns variations that might match the same root:
        - Different plural forms
        - Different case endings
        """
        root = self.get_root(word)
        variants = {root}

        # Add common plural variants
        if not root.endswith(('lar', 'ler')):
            # Vowel harmony rules (simplified)
            last_vowel = self._get_last_vowel(root)
            if last_vowel in ['a', 'ı', 'o', 'u']:
                variants.add(root + 'lar')
            else:
                variants.add(root + 'ler')

        return list(variants)

    def _get_last_vowel(self, word: str) -> Optional[str]:
        """Get the last vowel in a word (for vowel harmony)"""
        vowels = 'aeıioöuü'
        for char in reversed(word):
            if char in vowels:
                return char
        return None

    def is_turkish_word(self, word: str) -> bool:
        """
        Check if a word appears to be Turkish

        Simple heuristic: contains Turkish-specific characters
        """
        turkish_chars = set('ğüşıöçĞÜŞİÖÇ')
        return any(c in turkish_chars for c in word)

    def suggest_corrections(self, word: str) -> List[str]:
        """
        Suggest corrections for potentially misspelled words

        Returns:
            List of suggested corrections
        """
        # Common typos in Turkish keyboard
        typo_map = {
            'ii': 'ı',
            'sh': 'ş',
            'ch': 'ç',
            'gh': 'ğ',
        }

        suggestions = []
        normalized = word.lower()

        for typo, correct in typo_map.items():
            if typo in normalized:
                suggestion = normalized.replace(typo, correct)
                suggestions.append(suggestion)

        return suggestions
