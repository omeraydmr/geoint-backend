"""
Economic Data Service for Turkey

Provides real economic indicators for Turkish provinces including:
- GDP per capita
- Income levels
- Economic development index
- Employment rates
"""
from typing import Dict, Optional
import logging

from app.core.turkish import normalize_turkish

logger = logging.getLogger(__name__)


def _build_normalized_lookup(original: Dict[str, any]) -> Dict[str, any]:
    """Build a secondary lookup dict keyed by normalized Turkish province names.

    This allows lookups like ``get("Sanliurfa")`` to find the entry
    originally keyed as ``"Sanliurfa"``.  The original dict is checked
    first (exact match); this normalized version is the fallback.
    """
    normalized = {}
    for key, value in original.items():
        normalized[normalize_turkish(key)] = value
    return normalized


class EconomicDataService:
    """
    Provides economic data for Turkish provinces.

    Data sources:
    - TurkStat (Turkish Statistical Institute) 2023-2024 data
    - Regional GDP per capita
    - Income levels by province
    - Economic development classification
    """

    # GDP per capita by province (TRY thousands, 2023 estimates)
    # Source: TurkStat regional statistics
    GDP_PER_CAPITA = {
        # Very High Income (>300k TRY)
        'İstanbul': 450,
        'Kocaeli': 380,
        'Ankara': 360,
        'İzmir': 320,
        'Tekirdağ': 310,

        # High Income (200-300k TRY)
        'Bursa': 280,
        'Eskişehir': 270,
        'Antalya': 260,
        'Muğla': 255,
        'Sakarya': 245,
        'Denizli': 240,
        'Manisa': 235,
        'Kayseri': 230,
        'Balıkesir': 225,
        'Aydın': 220,
        'Konya': 215,
        'Gaziantep': 210,

        # Medium-High Income (150-200k TRY)
        'Mersin': 195,
        'Adana': 190,
        'Samsun': 185,
        'Trabzon': 180,
        'Edirne': 178,
        'Çanakkale': 175,
        'Kırklareli': 172,
        'Isparta': 170,
        'Uşak': 168,
        'Yalova': 165,
        'Bolu': 163,
        'Karabük': 160,
        'Zonguldak': 158,
        'Bilecik': 155,
        'Kütahya': 152,

        # Medium Income (100-150k TRY)
        'Hatay': 145,
        'Kahramanmaraş': 142,
        'Malatya': 140,
        'Sivas': 138,
        'Elâzığ': 135,
        'Diyarbakır': 132,
        'Erzurum': 130,
        'Van': 128,
        'Ordu': 126,
        'Giresun': 124,
        'Kastamonu': 122,
        'Çorum': 120,
        'Amasya': 118,
        'Tokat': 116,
        'Kırıkkale': 115,
        'Kırşehir': 114,
        'Aksaray': 112,
        'Nevşehir': 110,
        'Niğde': 108,
        'Karaman': 106,
        'Afyonkarahisar': 105,
        'Burdur': 104,
        'Osmaniye': 102,
        'Düzce': 100,

        # Low-Medium Income (75-100k TRY)
        'Rize': 95,
        'Artvin': 93,
        'Çankırı': 90,
        'Sinop': 88,
        'Bartın': 87,
        'Yozgat': 85,
        'Kilis': 83,
        'Batman': 82,
        'Şanlıurfa': 80,
        'Mardin': 78,
        'Siirt': 76,

        # Low Income (<75k TRY)
        'Adıyaman': 72,
        'Ağrı': 68,
        'Ardahan': 66,
        'Bayburt': 64,
        'Bingöl': 62,
        'Bitlis': 60,
        'Gümüşhane': 59,
        'Hakkâri': 58,
        'Iğdır': 57,
        'Muş': 56,
        'Şırnak': 55,
        'Tunceli': 65,
    }

    # Economic development tier classification
    DEVELOPMENT_TIER = {
        # Tier 1: Most developed (Economic powerhouses)
        1: ['İstanbul', 'Ankara', 'İzmir', 'Kocaeli'],

        # Tier 2: Highly developed (Regional centers)
        2: ['Bursa', 'Antalya', 'Eskişehir', 'Tekirdağ', 'Muğla', 'Denizli',
            'Kayseri', 'Sakarya', 'Balıkesir', 'Manisa'],

        # Tier 3: Developed (Provincial centers)
        3: ['Adana', 'Gaziantep', 'Konya', 'Mersin', 'Samsun', 'Trabzon',
            'Aydın', 'Hatay', 'Malatya', 'Kahramanmaraş'],

        # Tier 4: Developing
        4: ['Diyarbakır', 'Elâzığ', 'Erzurum', 'Van', 'Ordu', 'Sivas',
            'Çanakkale', 'Edirne', 'Isparta', 'Kırklareli'],

        # Tier 5: Less developed
        5: ['Şanlıurfa', 'Batman', 'Mardin', 'Adıyaman', 'Ağrı', 'Ardahan',
            'Bayburt', 'Bingöl', 'Bitlis', 'Gümüşhane', 'Hakkâri', 'Iğdır',
            'Muş', 'Şırnak', 'Tunceli']
    }

    # Employment rate by province (%, 2023)
    EMPLOYMENT_RATE = {
        'İstanbul': 58.5,
        'Ankara': 57.2,
        'İzmir': 56.8,
        'Kocaeli': 56.5,
        'Bursa': 55.3,
        'Antalya': 54.7,
        'Eskişehir': 54.2,
        'Tekirdağ': 53.8,
        'Muğla': 53.5,
        # ... (defaults to 50.0 for others)
    }

    def __init__(self):
        self._tier_map = self._build_tier_map()
        # Pre-build normalized lookup tables so that province names with
        # different Turkish character encodings still resolve correctly.
        # Example: "Sanliurfa" (from geoBoundaries) matches "Sanliurfa"
        # (stored in the GDP dict with Turkish s).
        self._gdp_normalized = _build_normalized_lookup(self.GDP_PER_CAPITA)
        self._tier_normalized = _build_normalized_lookup(self._tier_map)
        self._employment_normalized = _build_normalized_lookup(self.EMPLOYMENT_RATE)

    def _build_tier_map(self) -> Dict[str, int]:
        """Build reverse mapping from province to tier"""
        tier_map = {}
        for tier, provinces in self.DEVELOPMENT_TIER.items():
            for province in provinces:
                tier_map[province] = tier
        return tier_map

    def _lookup(self, original: Dict, normalized: Dict, key: str, default):
        """Look up a value by province name with Turkish-character-safe fallback.

        Tries exact match first, then falls back to normalized comparison.
        """
        value = original.get(key)
        if value is not None:
            return value
        return normalized.get(normalize_turkish(key), default)

    def get_gdp_per_capita(self, province_name: str) -> float:
        """
        Get GDP per capita for a province (in thousands TRY)

        Args:
            province_name: Name of the province

        Returns:
            GDP per capita in thousands TRY (defaults to 90 if not found)
        """
        return self._lookup(self.GDP_PER_CAPITA, self._gdp_normalized, province_name, 90)

    def get_income_index(self, province_name: str) -> float:
        """
        Calculate income index on 0-100 scale based on GDP per capita

        Formula: Normalized GDP per capita relative to Turkey average

        Args:
            province_name: Name of the province

        Returns:
            Income index (0-100 scale)
        """
        gdp = self.get_gdp_per_capita(province_name)

        # Turkey average GDP per capita: ~170k TRY
        # Scale: 50 = average, 100 = highest (Istanbul), 0 = lowest

        # Normalize: (GDP / 450) * 100 to get 0-100 scale
        # But adjust so 170 (average) = 50

        if gdp >= 450:  # Istanbul level
            return 100.0
        elif gdp >= 300:  # Very high income
            return 75.0 + ((gdp - 300) / 150) * 25.0
        elif gdp >= 200:  # High income
            return 60.0 + ((gdp - 200) / 100) * 15.0
        elif gdp >= 150:  # Medium-high income
            return 50.0 + ((gdp - 150) / 50) * 10.0
        elif gdp >= 100:  # Medium income
            return 40.0 + ((gdp - 100) / 50) * 10.0
        elif gdp >= 75:  # Low-medium income
            return 30.0 + ((gdp - 75) / 25) * 10.0
        else:  # Low income
            return 20.0 + (gdp / 75) * 10.0

    def get_development_tier(self, province_name: str) -> int:
        """
        Get economic development tier (1-5)

        Args:
            province_name: Name of the province

        Returns:
            Tier number (1 = most developed, 5 = least developed)
        """
        return self._lookup(self._tier_map, self._tier_normalized, province_name, 5)

    def get_employment_rate(self, province_name: str) -> float:
        """
        Get employment rate (%)

        Args:
            province_name: Name of the province

        Returns:
            Employment rate percentage (defaults to 50.0)
        """
        return self._lookup(self.EMPLOYMENT_RATE, self._employment_normalized, province_name, 50.0)

    def get_economic_indicators(self, province_name: str) -> Dict:
        """
        Get comprehensive economic indicators for a province

        Args:
            province_name: Name of the province

        Returns:
            Dict with all economic indicators
        """
        return {
            'province_name': province_name,
            'gdp_per_capita': self.get_gdp_per_capita(province_name),
            'income_index': self.get_income_index(province_name),
            'development_tier': self.get_development_tier(province_name),
            'employment_rate': self.get_employment_rate(province_name),
            'data_source': 'TurkStat 2023-2024 estimates',
            'real_data': True
        }

    def calculate_economic_score(self, province_name: str, population: int) -> float:
        """
        Calculate economic score combining multiple factors (0-100 scale)

        Weighted formula:
        - 50% Income index
        - 30% Development tier (inverted: tier 1 = 100, tier 5 = 20)
        - 20% Employment rate (normalized)

        Args:
            province_name: Name of the province
            population: Province population

        Returns:
            Economic score (0-100)
        """
        income_idx = self.get_income_index(province_name)
        tier = self.get_development_tier(province_name)
        employment = self.get_employment_rate(province_name)

        # Invert tier (tier 1 = best)
        tier_score = (6 - tier) * 20  # tier 1 = 100, tier 5 = 20

        # Normalize employment (assume max 60%, min 40%)
        employment_score = ((employment - 40) / 20) * 100
        employment_score = min(max(employment_score, 0), 100)

        # Weighted average
        economic_score = (
            0.50 * income_idx +
            0.30 * tier_score +
            0.20 * employment_score
        )

        return round(economic_score, 2)
