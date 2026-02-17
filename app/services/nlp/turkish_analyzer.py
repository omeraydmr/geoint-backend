"""
Turkish NLP Analyzer

Provides high-level keyword analysis combining Zemberek morphological analysis
with intent classification and keyword validation.
"""
from typing import Dict, List, Optional
from app.services.nlp.zemberek_client import ZemberekClient


class TurkishNLPAnalyzer:
    """
    High-level Turkish NLP analyzer for keyword analysis

    Combines:
    - Morphological analysis (via Zemberek)
    - Intent classification
    - Keyword validation
    - Variation generation
    """

    # Intent keywords mapping
    INTENT_KEYWORDS = {
        'informational': [
            'nedir', 'nasıl', 'ne', 'kim', 'neden', 'niçin', 'hangi',
            'hakkında', 'bilgi', 'öğren', 'anlat', 'açıkla'
        ],
        'transactional': [
            'satın', 'al', 'sipariş', 'fiyat', 'ucuz', 'indirim',
            'kampanya', 'satış', 'mağaza', 'online', 'kargo'
        ],
        'navigational': [
            'giriş', 'login', 'anasayfa', 'site', 'sayfa', 'resmi',
            'iletişim', 'adres', 'telefon'
        ],
        'commercial': [
            'en iyi', 'karşılaştır', 'vs', 'yorum', 'değerlendirme',
            'tavsiye', 'öneri', 'review', 'test'
        ]
    }

    def __init__(self):
        self.zemberek = ZemberekClient()

    def analyze_keyword(self, keyword: str) -> Dict:
        """
        Perform comprehensive keyword analysis

        Args:
            keyword: Keyword text to analyze

        Returns:
            Dict with keys:
            - keyword: original keyword
            - root_form: root/stem form
            - intent: detected search intent
            - pos: part of speech
            - variations: keyword variations
            - is_valid: whether keyword is valid
            - word_count: number of words
            - contains_turkish: has Turkish-specific characters
        """
        # Normalize and get basic analysis
        normalized = self.zemberek.normalize(keyword)
        words = normalized.split()

        # Analyze each word
        word_analyses = []
        roots = []

        for word in words:
            analysis = self.zemberek.analyze(word)
            word_analyses.append(analysis)
            roots.append(analysis.get('root', word))

        # Get root form (combine all roots)
        root_form = ' '.join(roots)

        # Detect intent
        intent = self._detect_intent(normalized)

        # Generate variations
        variations = self._generate_variations(keyword, roots)

        # Validate keyword
        is_valid = self._validate_keyword(keyword, normalized)

        # Check if contains Turkish characters
        contains_turkish = self.zemberek.is_turkish_word(keyword)

        return {
            'keyword': keyword,
            'root_form': root_form,
            'intent': intent,
            'pos': word_analyses[0].get('pos', 'Unknown') if word_analyses else 'Unknown',
            'variations': variations,
            'is_valid': is_valid,
            'word_count': len(words),
            'contains_turkish': contains_turkish,
            'normalized': normalized
        }

    def _detect_intent(self, text: str) -> str:
        """
        Detect search intent from keyword text

        Args:
            text: Normalized keyword text

        Returns:
            Intent type: informational, transactional, navigational, commercial
        """
        text_lower = text.lower()

        # Check for intent signals
        intent_scores = {intent: 0 for intent in self.INTENT_KEYWORDS}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    intent_scores[intent] += 1

        # Return intent with highest score, default to informational
        max_intent = max(intent_scores, key=intent_scores.get)

        if intent_scores[max_intent] == 0:
            return 'informational'  # Default intent

        return max_intent

    def _generate_variations(self, keyword: str, roots: List[str]) -> List[str]:
        """
        Generate keyword variations for search expansion

        Args:
            keyword: Original keyword
            roots: List of root words

        Returns:
            List of keyword variations
        """
        variations = set()

        # Add normalized version
        variations.add(self.zemberek.normalize(keyword))

        # Add root form
        variations.add(' '.join(roots))

        # Add stem variants for each word
        for root in roots:
            variants = self.zemberek.get_stem_variants(root)
            for variant in variants:
                variations.add(variant)

        # Remove original keyword from variations
        variations.discard(keyword)
        variations.discard(keyword.lower())

        return list(variations)[:10]  # Limit to 10 variations

    def _validate_keyword(self, keyword: str, normalized: str) -> bool:
        """
        Validate if keyword is suitable for analysis

        Args:
            keyword: Original keyword
            normalized: Normalized keyword

        Returns:
            True if valid keyword
        """
        # Minimum length check
        if len(normalized) < 2:
            return False

        # Maximum length check
        if len(normalized) > 200:
            return False

        # Check for at least one letter
        if not any(c.isalpha() for c in normalized):
            return False

        # Check for excessive special characters
        special_chars = sum(1 for c in keyword if not c.isalnum() and c != ' ')
        if special_chars > len(keyword) * 0.3:
            return False

        return True

    def batch_analyze(self, keywords: List[str]) -> List[Dict]:
        """
        Analyze multiple keywords

        Args:
            keywords: List of keywords to analyze

        Returns:
            List of analysis results
        """
        return [self.analyze_keyword(kw) for kw in keywords]

    def get_suggestions(self, keyword: str) -> List[str]:
        """
        Get spelling suggestions for a keyword

        Args:
            keyword: Keyword to check

        Returns:
            List of suggested corrections
        """
        words = keyword.split()
        suggestions = []

        for word in words:
            word_suggestions = self.zemberek.suggest_corrections(word)
            suggestions.extend(word_suggestions)

        return suggestions
