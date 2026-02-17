"""
Keyword Grouper and Intent Classifier for Turkish keywords
"""
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from app.services.nlp.zemberek_client import ZemberekClient


class KeywordGrouper:
    """
    Groups related keywords and classifies search intent

    Intent Types (following Google's framework adapted for Turkish):
    - Transactional: "satın al", "fiyat", "sipariş"
    - Informational: "nedir", "nasıl", "ne zaman"
    - Navigational: "giriş", "login", "site"
    - Commercial: "en iyi", "karşılaştır", "inceleme"
    """

    def __init__(self):
        self.zemberek = ZemberekClient()

        # Intent classification patterns (Turkish)
        self.intent_patterns = {
            'transactional': [
                'satın al', 'al', 'fiyat', 'fiyatı', 'ucuz', 'indirim',
                'sipariş', 'kampanya', 'sepet', 'ödeme', 'kredi kartı',
                'ücretsiz kargo', 'hızlı teslimat', 'aynı gün',
                'taksit', 'peşin', 'satılık'
            ],
            'informational': [
                'nedir', 'ne demek', 'nasıl', 'ne zaman', 'neden',
                'niçin', 'kim', 'nerede', 'hangi', 'kaç',
                'anlat', 'açıkla', 'bilgi', 'hakkında', 'tarif',
                'öğren', 'örnekler', 'guide', 'rehber'
            ],
            'navigational': [
                'giriş', 'login', 'kayıt', 'üye', 'hesap',
                'site', 'website', 'resmi', 'iletişim',
                'müşteri hizmetleri', 'destek', 'yardım'
            ],
            'commercial': [
                'en iyi', 'top', 'karşılaştır', 'vs', 'farkı',
                'hangi', 'öneri', 'tavsiye', 'inceleme', 'yorum',
                'review', 'alternatif', 'değerlendirme', 'puanlama',
                'en ucuz', 'en kaliteli', 'markaları'
            ]
        }

        # Stop words (Turkish)
        self.stop_words = {
            've', 'ile', 'için', 'de', 'da', 'bir', 'bu', 'şu', 'o',
            'ne', 'mi', 'mı', 'mu', 'mü', 'olan', 'olarak', 'gibi',
            'daha', 'çok', 'en', 'var', 'yok', 'her', 'tüm'
        }

    def group_keywords(
        self,
        keywords: List[str],
        by_root: bool = True
    ) -> Dict[str, List[str]]:
        """
        Group related keywords together

        Args:
            keywords: List of keywords to group
            by_root: Group by root form (True) or exact match (False)

        Returns:
            Dict mapping group key to list of keywords
        """
        groups = defaultdict(list)

        for keyword in keywords:
            group_key = self._create_group_key(keyword, by_root)
            groups[group_key].append(keyword)

        return dict(groups)

    def classify_intent(self, keyword: str) -> str:
        """
        Classify keyword search intent

        Args:
            keyword: Keyword to classify

        Returns:
            Intent type: 'transactional', 'informational', 'navigational', 'commercial', or 'unknown'
        """
        keyword_lower = self.zemberek.normalize(keyword)

        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in keyword_lower:
                    return intent

        # Default: if contains question words -> informational
        question_words = ['nedir', 'nasıl', 'neden', 'ne', 'kim', 'nerede']
        if any(qw in keyword_lower for qw in question_words):
            return 'informational'

        # Default: unknown
        return 'unknown'

    def classify_bulk(
        self,
        keywords: List[str]
    ) -> Dict[str, List[str]]:
        """
        Classify multiple keywords by intent

        Args:
            keywords: List of keywords

        Returns:
            Dict mapping intent to list of keywords
        """
        intent_groups = defaultdict(list)

        for keyword in keywords:
            intent = self.classify_intent(keyword)
            intent_groups[intent].append(keyword)

        return dict(intent_groups)

    def extract_topics(
        self,
        keywords: List[str],
        min_frequency: int = 2
    ) -> List[Tuple[str, int]]:
        """
        Extract common topics/terms from keywords

        Args:
            keywords: List of keywords
            min_frequency: Minimum occurrence to be considered a topic

        Returns:
            List of (topic, frequency) tuples, sorted by frequency
        """
        # Extract roots from all keywords
        roots = []
        for keyword in keywords:
            words = keyword.split()
            for word in words:
                if word.lower() not in self.stop_words:
                    root = self.zemberek.get_root(word)
                    roots.append(root)

        # Count frequencies
        freq = defaultdict(int)
        for root in roots:
            freq[root] += 1

        # Filter by minimum frequency and sort
        topics = [
            (root, count)
            for root, count in freq.items()
            if count >= min_frequency
        ]

        return sorted(topics, key=lambda x: x[1], reverse=True)

    def find_long_tail(
        self,
        keywords: List[str],
        min_words: int = 3
    ) -> List[str]:
        """
        Find long-tail keywords (multi-word phrases)

        Args:
            keywords: List of keywords
            min_words: Minimum number of words to be considered long-tail

        Returns:
            List of long-tail keywords
        """
        long_tail = []

        for keyword in keywords:
            word_count = len(keyword.split())
            if word_count >= min_words:
                long_tail.append(keyword)

        return long_tail

    def suggest_variations(
        self,
        keyword: str,
        max_suggestions: int = 10
    ) -> List[str]:
        """
        Suggest keyword variations using Turkish grammar rules

        Args:
            keyword: Base keyword
            max_suggestions: Maximum number of suggestions

        Returns:
            List of keyword variations
        """
        variations = set()
        words = keyword.split()

        if not words:
            return []

        # Get root of main word (last word usually carries main meaning)
        main_word = words[-1]
        root = self.zemberek.get_root(main_word)

        # Add plural forms
        if not main_word.endswith(('lar', 'ler')):
            last_vowel = self.zemberek._get_last_vowel(root)
            if last_vowel in ['a', 'ı', 'o', 'u']:
                variations.add(keyword + 'lar')
            else:
                variations.add(keyword + 'ler')

        # Add location markers
        variations.add(keyword + ' nerede')
        variations.add(keyword + ' nasıl')
        variations.add(keyword + ' fiyatları')
        variations.add('en iyi ' + keyword)
        variations.add(keyword + ' satın al')

        # Add question forms
        variations.add(keyword + ' nedir')

        return list(variations)[:max_suggestions]

    def _create_group_key(self, keyword: str, by_root: bool) -> str:
        """
        Create a grouping key for a keyword

        Args:
            keyword: Keyword to create key for
            by_root: Use root forms

        Returns:
            Group key
        """
        words = keyword.split()

        if by_root:
            # Get roots of all non-stop words
            roots = [
                self.zemberek.get_root(w)
                for w in words
                if w.lower() not in self.stop_words
            ]
            # Sort to group similar phrases regardless of word order
            return '_'.join(sorted(roots))
        else:
            # Use normalized exact words
            normalized = [
                self.zemberek.normalize(w)
                for w in words
                if w.lower() not in self.stop_words
            ]
            return '_'.join(sorted(normalized))

    def calculate_similarity(self, keyword1: str, keyword2: str) -> float:
        """
        Calculate similarity between two keywords (0-1)

        Uses Jaccard similarity of root words

        Args:
            keyword1: First keyword
            keyword2: Second keyword

        Returns:
            Similarity score (0 = no similarity, 1 = identical)
        """
        # Get root words
        roots1 = set(
            self.zemberek.get_root(w)
            for w in keyword1.split()
            if w.lower() not in self.stop_words
        )

        roots2 = set(
            self.zemberek.get_root(w)
            for w in keyword2.split()
            if w.lower() not in self.stop_words
        )

        # Jaccard similarity
        if not roots1 or not roots2:
            return 0.0

        intersection = len(roots1 & roots2)
        union = len(roots1 | roots2)

        return intersection / union if union > 0 else 0.0
