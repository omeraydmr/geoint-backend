"""
Google Trends Collector for Turkey

Collects search trend data at province and national level
"""
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


class GoogleTrendsCollector:
    """
    Collect Google Trends data for Turkish regions

    Uses pytrends library to fetch:
    - Regional interest by province
    - Interest over time
    - Related queries
    """

    # Turkish province codes (ISO 3166-2:TR)
    TURKEY_PROVINCES = {
        'TR-01': 'Adana', 'TR-02': 'Adıyaman', 'TR-03': 'Afyonkarahisar',
        'TR-04': 'Ağrı', 'TR-05': 'Amasya', 'TR-06': 'Ankara',
        'TR-07': 'Antalya', 'TR-08': 'Artvin', 'TR-09': 'Aydın',
        'TR-10': 'Balıkesir', 'TR-11': 'Bilecik', 'TR-12': 'Bingöl',
        'TR-13': 'Bitlis', 'TR-14': 'Bolu', 'TR-15': 'Burdur',
        'TR-16': 'Bursa', 'TR-17': 'Çanakkale', 'TR-18': 'Çankırı',
        'TR-19': 'Çorum', 'TR-20': 'Denizli', 'TR-21': 'Diyarbakır',
        'TR-22': 'Edirne', 'TR-23': 'Elazığ', 'TR-24': 'Erzincan',
        'TR-25': 'Erzurum', 'TR-26': 'Eskişehir', 'TR-27': 'Gaziantep',
        'TR-28': 'Giresun', 'TR-29': 'Gümüşhane', 'TR-30': 'Hakkâri',
        'TR-31': 'Hatay', 'TR-32': 'Isparta', 'TR-33': 'Mersin',
        'TR-34': 'İstanbul', 'TR-35': 'İzmir', 'TR-36': 'Kars',
        'TR-37': 'Kastamonu', 'TR-38': 'Kayseri', 'TR-39': 'Kırklareli',
        'TR-40': 'Kırşehir', 'TR-41': 'Kocaeli', 'TR-42': 'Konya',
        'TR-43': 'Kütahya', 'TR-44': 'Malatya', 'TR-45': 'Manisa',
        'TR-46': 'Kahramanmaraş', 'TR-47': 'Mardin', 'TR-48': 'Muğla',
        'TR-49': 'Muş', 'TR-50': 'Nevşehir', 'TR-51': 'Niğde',
        'TR-52': 'Ordu', 'TR-53': 'Rize', 'TR-54': 'Sakarya',
        'TR-55': 'Samsun', 'TR-56': 'Siirt', 'TR-57': 'Sinop',
        'TR-58': 'Sivas', 'TR-59': 'Tekirdağ', 'TR-60': 'Tokat',
        'TR-61': 'Trabzon', 'TR-62': 'Tunceli', 'TR-63': 'Şanlıurfa',
        'TR-64': 'Uşak', 'TR-65': 'Van', 'TR-66': 'Yozgat',
        'TR-67': 'Zonguldak', 'TR-68': 'Aksaray', 'TR-69': 'Bayburt',
        'TR-70': 'Karaman', 'TR-71': 'Kırıkkale', 'TR-72': 'Batman',
        'TR-73': 'Şırnak', 'TR-74': 'Bartın', 'TR-75': 'Ardahan',
        'TR-76': 'Iğdır', 'TR-77': 'Yalova', 'TR-78': 'Karabük',
        'TR-79': 'Kilis', 'TR-80': 'Osmaniye', 'TR-81': 'Düzce'
    }

    def __init__(self):
        self._pytrends = None
        self._last_request_time = None
        self._min_delay = 2  # Minimum 2 seconds between requests

    def _get_pytrends(self):
        """Lazy initialization of pytrends client"""
        if self._pytrends is None:
            try:
                from pytrends.request import TrendReq
                self._pytrends = TrendReq(hl='tr-TR', tz=-180)
                logger.info("✅ Google Trends client initialized")
            except ImportError:
                logger.error("❌ pytrends not installed. Install with: pip install pytrends")
                raise

        return self._pytrends

    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self._min_delay:
                await asyncio.sleep(self._min_delay - elapsed)

        self._last_request_time = datetime.now()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=60))
    async def get_region_interest(
        self,
        keyword: str,
        geo: str = 'TR',
        timeframe: str = 'today 12-m'
    ) -> Dict[str, Dict]:
        """
        Get interest by region for a keyword

        Args:
            keyword: Keyword to search for
            geo: Geographic code (TR for Turkey, or TR-34 for Istanbul)
            timeframe: Time period ('today 12-m', 'today 3-m', 'now 7-d')

        Returns:
            Dict mapping province code to interest data
        """
        await self._rate_limit()

        pytrends = self._get_pytrends()

        # Build payload
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.build_payload([keyword], geo=geo, timeframe=timeframe)
        )

        # Get regional interest
        df = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.interest_by_region(resolution='REGION', inc_geo_code=True)
        )

        # Convert to dict
        results = {}
        for province_name, row in df.iterrows():
            # Get geo code from the geoCode column
            geo_code = row.get('geoCode', '')
            if geo_code and geo_code.startswith('TR-'):
                code = geo_code.split('-')[1]  # Extract numeric code (e.g., "34" from "TR-34")
                results[code] = {
                    'value': int(row[keyword]) if keyword in row else 0,
                    'name': province_name,  # Use the actual province name from index
                    'geo_code': geo_code
                }

        logger.info(f"📊 Got trends data for '{keyword}' - {len(results)} provinces")
        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=60))
    async def get_interest_over_time(
        self,
        keyword: str,
        geo: str = 'TR',
        timeframe: str = 'today 12-m'
    ) -> List[Dict]:
        """
        Get interest over time for a keyword

        Args:
            keyword: Keyword to search for
            geo: Geographic code
            timeframe: Time period

        Returns:
            List of {date, value} dicts
        """
        await self._rate_limit()

        pytrends = self._get_pytrends()

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.build_payload([keyword], geo=geo, timeframe=timeframe)
        )

        df = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.interest_over_time()
        )

        if df.empty or keyword not in df.columns:
            return []

        results = []
        for date, row in df.iterrows():
            results.append({
                'date': date.isoformat(),
                'value': int(row[keyword])
            })

        return results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=60))
    async def get_related_queries(
        self,
        keyword: str,
        geo: str = 'TR'
    ) -> Dict[str, List[Dict]]:
        """
        Get related queries (rising and top)

        Args:
            keyword: Keyword to search for
            geo: Geographic code

        Returns:
            Dict with 'rising' and 'top' lists of related queries
        """
        await self._rate_limit()

        pytrends = self._get_pytrends()

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.build_payload([keyword], geo=geo, timeframe='today 12-m')
        )

        related = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pytrends.related_queries()
        )

        results = {'rising': [], 'top': []}

        if keyword in related:
            # Rising queries
            if related[keyword]['rising'] is not None:
                rising_df = related[keyword]['rising']
                results['rising'] = rising_df.to_dict('records')

            # Top queries
            if related[keyword]['top'] is not None:
                top_df = related[keyword]['top']
                results['top'] = top_df.to_dict('records')

        return results

    async def calculate_trend_metrics(
        self,
        interest_over_time: List[Dict]
    ) -> Dict:
        """
        Calculate trend metrics from time series data

        Args:
            interest_over_time: List of {date, value} dicts

        Returns:
            Dict with yoy_change, mom_change, trend, etc.
        """
        if not interest_over_time or len(interest_over_time) < 2:
            return {
                'yoy_change': 0,
                'mom_change': 0,
                'trend': 'stable',
                'avg_interest': 0
            }

        values = [d['value'] for d in interest_over_time]
        avg_interest = sum(values) / len(values)

        # Month-over-month change (last month vs previous month)
        if len(values) >= 8:  # Need at least 8 weeks
            recent_month = values[-4:]  # Last 4 weeks
            previous_month = values[-8:-4]  # Previous 4 weeks

            recent_avg = sum(recent_month) / len(recent_month)
            previous_avg = sum(previous_month) / len(previous_month)

            if previous_avg > 0:
                mom_change = ((recent_avg - previous_avg) / previous_avg) * 100
            else:
                mom_change = 0
        else:
            mom_change = 0

        # Year-over-year (if we have 12 months of data)
        if len(values) >= 52:  # 52 weeks = 1 year
            recent_avg = sum(values[-4:]) / 4
            year_ago_avg = sum(values[0:4]) / 4

            if year_ago_avg > 0:
                yoy_change = ((recent_avg - year_ago_avg) / year_ago_avg) * 100
            else:
                yoy_change = 0
        else:
            yoy_change = 0

        # Determine trend
        if mom_change > 10:
            trend = 'rising'
        elif mom_change < -10:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'yoy_change': round(yoy_change, 2),
            'mom_change': round(mom_change, 2),
            'trend': trend,
            'avg_interest': round(avg_interest, 2),
            'current_interest': values[-1] if values else 0,
            'peak_interest': max(values) if values else 0
        }

    def get_province_code_by_name(self, province_name: str) -> Optional[str]:
        """
        Get province code from name.

        Supports Turkish-character-safe matching so that both
        "Sanliurfa" and "Sanliurfa" resolve to code "63".

        Args:
            province_name: Province name (e.g., "Istanbul" or "Istanbul")

        Returns:
            Province code (e.g., "34") or None
        """
        from app.core.turkish import normalize_turkish

        # Try exact match first (fast path)
        name_lower = province_name.lower()
        for code, name in self.TURKEY_PROVINCES.items():
            if name.lower() == name_lower:
                return code.split('-')[1]

        # Fallback: normalized Turkish comparison
        normalized_input = normalize_turkish(province_name)
        for code, name in self.TURKEY_PROVINCES.items():
            if normalize_turkish(name) == normalized_input:
                return code.split('-')[1]

        return None
