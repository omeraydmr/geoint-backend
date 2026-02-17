"""
DataForSEO API Integration

Provides SEO data, keyword research, and competitor analysis.

API Documentation: https://docs.dataforseo.com/
"""
from typing import List, Dict, Optional
import httpx
import base64
import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentRequiredError(Exception):
    """Raised when DataForSEO account has insufficient credits (402 error)"""
    pass


# DataForSEO location codes for Turkish provinces
# Reference: https://docs.dataforseo.com/v3/serp/google/locations/
TURKEY_PROVINCE_LOCATION_CODES = {
    "01": 20614,   # Adana
    "02": 20615,   # Adiyaman
    "03": 20616,   # Afyonkarahisar
    "04": 20617,   # Agri
    "05": 20618,   # Amasya
    "06": 20766,   # Ankara
    "07": 20777,   # Antalya
    "08": 20778,   # Artvin
    "09": 20779,   # Aydin
    "10": 20780,   # Balikesir
    "11": 20781,   # Bilecik
    "12": 20782,   # Bingol
    "13": 20783,   # Bitlis
    "14": 20784,   # Bolu
    "15": 20785,   # Burdur
    "16": 20886,   # Bursa
    "17": 20887,   # Canakkale
    "18": 20888,   # Cankiri
    "19": 20889,   # Corum
    "20": 20890,   # Denizli
    "21": 20891,   # Diyarbakir
    "22": 20892,   # Edirne
    "23": 20893,   # Elazig
    "24": 20894,   # Erzincan
    "25": 20895,   # Erzurum
    "26": 20896,   # Eskisehir
    "27": 20897,   # Gaziantep
    "28": 20898,   # Giresun
    "29": 20899,   # Gumushane
    "30": 20900,   # Hakkari
    "31": 20901,   # Hatay
    "32": 20902,   # Isparta
    "33": 20903,   # Mersin (Icel)
    "34": 21176,   # Istanbul
    "35": 21012,   # Izmir
    "36": 21013,   # Kars
    "37": 21014,   # Kastamonu
    "38": 21015,   # Kayseri
    "39": 21016,   # Kirklareli
    "40": 21017,   # Kirsehir
    "41": 21018,   # Kocaeli
    "42": 21019,   # Konya
    "43": 21020,   # Kutahya
    "44": 21021,   # Malatya
    "45": 21022,   # Manisa
    "46": 21023,   # Kahramanmaras
    "47": 21024,   # Mardin
    "48": 21025,   # Mugla
    "49": 21026,   # Mus
    "50": 21027,   # Nevsehir
    "51": 21028,   # Nigde
    "52": 21029,   # Ordu
    "53": 21030,   # Rize
    "54": 21031,   # Sakarya
    "55": 21032,   # Samsun
    "56": 21033,   # Siirt
    "57": 21034,   # Sinop
    "58": 21035,   # Sivas
    "59": 21036,   # Tekirdag
    "60": 21037,   # Tokat
    "61": 21038,   # Trabzon
    "62": 21039,   # Tunceli
    "63": 21040,   # Sanliurfa
    "64": 21041,   # Usak
    "65": 21042,   # Van
    "66": 21043,   # Yozgat
    "67": 21044,   # Zonguldak
    "68": 21045,   # Aksaray
    "69": 21046,   # Bayburt
    "70": 21047,   # Karaman
    "71": 21048,   # Kirikkale
    "72": 21049,   # Batman
    "73": 21050,   # Sirnak
    "74": 21051,   # Bartin
    "75": 21052,   # Ardahan
    "76": 21053,   # Igdir
    "77": 21054,   # Yalova
    "78": 21055,   # Karabuk
    "79": 21056,   # Kilis
    "80": 21057,   # Osmaniye
    "81": 21058,   # Duzce
}

# Province names by code
TURKEY_PROVINCE_NAMES = {
    "01": "Adana", "02": "Adiyaman", "03": "Afyonkarahisar", "04": "Agri",
    "05": "Amasya", "06": "Ankara", "07": "Antalya", "08": "Artvin",
    "09": "Aydin", "10": "Balikesir", "11": "Bilecik", "12": "Bingol",
    "13": "Bitlis", "14": "Bolu", "15": "Burdur", "16": "Bursa",
    "17": "Canakkale", "18": "Cankiri", "19": "Corum", "20": "Denizli",
    "21": "Diyarbakir", "22": "Edirne", "23": "Elazig", "24": "Erzincan",
    "25": "Erzurum", "26": "Eskisehir", "27": "Gaziantep", "28": "Giresun",
    "29": "Gumushane", "30": "Hakkari", "31": "Hatay", "32": "Isparta",
    "33": "Mersin", "34": "Istanbul", "35": "Izmir", "36": "Kars",
    "37": "Kastamonu", "38": "Kayseri", "39": "Kirklareli", "40": "Kirsehir",
    "41": "Kocaeli", "42": "Konya", "43": "Kutahya", "44": "Malatya",
    "45": "Manisa", "46": "Kahramanmaras", "47": "Mardin", "48": "Mugla",
    "49": "Mus", "50": "Nevsehir", "51": "Nigde", "52": "Ordu",
    "53": "Rize", "54": "Sakarya", "55": "Samsun", "56": "Siirt",
    "57": "Sinop", "58": "Sivas", "59": "Tekirdag", "60": "Tokat",
    "61": "Trabzon", "62": "Tunceli", "63": "Sanliurfa", "64": "Usak",
    "65": "Van", "66": "Yozgat", "67": "Zonguldak", "68": "Aksaray",
    "69": "Bayburt", "70": "Karaman", "71": "Kirikkale", "72": "Batman",
    "73": "Sirnak", "74": "Bartin", "75": "Ardahan", "76": "Igdir",
    "77": "Yalova", "78": "Karabuk", "79": "Kilis", "80": "Osmaniye",
    "81": "Duzce",
}


class DataForSEOClient:
    """
    DataForSEO API Client

    Requires:
    - DATAFORSEO_LOGIN: Your DataForSEO login email
    - DATAFORSEO_PASSWORD: Your DataForSEO password

    Get credentials from: https://app.dataforseo.com/register
    Free tier: $1 bonus credit
    """

    BASE_URL = "https://api.dataforseo.com/v3"

    # DataForSEO live SERP queries perform real-time Google searches.
    # They routinely take 15-45 seconds per request, especially for
    # location-specific queries. The timeout must accommodate this.
    SERP_TIMEOUT = httpx.Timeout(
        connect=10.0,
        read=80.0,
        write=10.0,
        pool=10.0,
    )
    DEFAULT_TIMEOUT = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=10.0,
    )

    def __init__(self):
        self.login = settings.DATAFORSEO_LOGIN
        self.password = settings.DATAFORSEO_PASSWORD
        self.client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)

        # Create Basic Auth header
        if self.login and self.password:
            credentials = f"{self.login}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            self.headers = {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json"
            }
            logger.info(
                "DataForSEO client initialized with credentials "
                "(login=%s, timeout=connect:10s/read:60s)",
                self.login,
            )
        else:
            self.headers = {}
            logger.warning(
                "DataForSEO client initialized WITHOUT credentials. "
                "All API calls will use fallback data. "
                "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in .env."
            )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def check_connectivity(self) -> bool:
        """
        Verify that DataForSEO API is reachable and credentials are valid.
        Uses a lightweight endpoint (locations list) that costs zero credits.
        Returns True if the API responds successfully, False otherwise.
        Intended for startup diagnostics -- call this once during app boot.
        """
        if not self.login or not self.password:
            logger.warning(
                "DataForSEO connectivity check skipped: no credentials configured"
            )
            return False

        diagnostic_url = f"{self.BASE_URL}/serp/google/locations"
        try:
            response = await self.client.get(
                diagnostic_url,
                headers=self.headers,
                timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            )
            if response.status_code == 200:
                data = response.json()
                task_count = len(data.get("tasks", []))
                logger.info(
                    "DataForSEO connectivity OK: status=200, tasks=%d",
                    task_count,
                )
                return True
            elif response.status_code == 401:
                logger.error(
                    "DataForSEO connectivity FAILED: 401 Unauthorized. "
                    "Check DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in .env."
                )
                return False
            elif response.status_code == 402:
                logger.error(
                    "DataForSEO connectivity FAILED: 402 Payment Required. "
                    "Account has insufficient credits."
                )
                return False
            else:
                logger.error(
                    "DataForSEO connectivity FAILED: unexpected status=%d, body=%s",
                    response.status_code,
                    response.text[:300],
                )
                return False
        except httpx.TimeoutException:
            logger.error(
                "DataForSEO connectivity FAILED: timeout reaching %s. "
                "Check network/firewall settings.",
                diagnostic_url,
            )
            return False
        except httpx.ConnectError as exc:
            logger.error(
                "DataForSEO connectivity FAILED: connection error (%s). "
                "DNS resolution or firewall may be blocking api.dataforseo.com.",
                exc,
            )
            return False
        except Exception as exc:
            logger.error(
                "DataForSEO connectivity FAILED: [%s] %s",
                type(exc).__name__,
                exc,
            )
            return False

    async def get_keyword_metrics(
        self,
        keywords: List[str],
        location_code: int = 2792,  # Turkey
        language_code: str = "tr"
    ) -> List[Dict]:
        """
        Get keyword metrics (search volume, CPC, competition)

        Args:
            keywords: List of keywords to analyze
            location_code: Geographic location (2792 = Turkey)
            language_code: Language code (tr = Turkish)

        Returns:
            List of keyword metrics
        """
        if not self.login or not self.password:
            return self._fallback_keyword_metrics(keywords)

        try:
            url = f"{self.BASE_URL}/keywords_data/google_ads/search_volume/live"

            payload = [{
                "keywords": keywords,
                "location_code": location_code,
                "language_code": language_code,
            }]

            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if not tasks or not tasks[0].get("result"):
                return self._fallback_keyword_metrics(keywords)

            results = []
            for item in tasks[0]["result"]:
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume", 0),
                    "competition": item.get("competition", 0),  # 0-1 scale
                    "cpc": item.get("cpc", 0),  # USD, convert to TL
                    "competition_level": item.get("competition_level", "UNKNOWN"),
                })

            logger.info(f"📊 Got metrics for {len(results)} keywords from DataForSEO")
            return results

        except Exception as e:
            logger.error(f"❌ Error getting keyword metrics: {e}")
            return self._fallback_keyword_metrics(keywords)

    async def get_serp_results(
        self,
        keyword: str,
        location_code: int = 2792,
        language_code: str = "tr",
        depth: int = 10
    ) -> List[Dict]:
        """
        Get Google SERP (Search Engine Results Page) data

        Args:
            keyword: Search query
            location_code: Geographic location
            language_code: Language
            depth: Number of results (1-100)

        Returns:
            List of organic search results
        """
        if not self.login or not self.password:
            return []

        try:
            url = f"{self.BASE_URL}/serp/google/organic/live/advanced"

            payload = [{
                "keyword": keyword,
                "location_code": location_code,
                "language_code": language_code,
                "depth": depth,
            }]

            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if not tasks or not tasks[0].get("result"):
                return []

            items = tasks[0]["result"][0].get("items", [])

            results = []
            for item in items:
                if item.get("type") == "organic":
                    results.append({
                        "position": item.get("rank_group", 0),
                        "url": item.get("url"),
                        "domain": item.get("domain"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                    })

            return results

        except Exception as e:
            logger.error(f"❌ Error getting SERP results: {e}")
            return []

    async def get_domain_metrics(
        self,
        domain: str,
        location_code: int = 2792
    ) -> Dict:
        """
        Get domain authority and SEO metrics

        Args:
            domain: Domain to analyze (e.g., "example.com")
            location_code: Geographic location (2792 = Turkey)

        Returns:
            Domain metrics including organic traffic and keywords
        """
        if not self.login or not self.password:
            return self._fallback_domain_metrics(domain)

        metrics = {
            "domain": domain,
            "domain_rank": 0,
            "backlinks": 0,
            "referring_domains": 0,
            "organic_etv": 0,
            "organic_keywords_count": 0,
        }

        # 1. Get backlink metrics
        try:
            url = f"{self.BASE_URL}/backlinks/summary/live"
            payload = [{"target": domain}]

            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if tasks and tasks[0].get("result"):
                result = tasks[0]["result"][0]
                metrics["domain_rank"] = result.get("rank", 0)
                metrics["backlinks"] = result.get("backlinks", 0)
                metrics["referring_domains"] = result.get("referring_domains", 0)
                logger.info(f"📊 Backlinks for {domain}: {metrics['backlinks']}")

        except Exception as e:
            logger.error(f"❌ Error getting backlink metrics for {domain}: {e}")

        # 2. Get organic traffic and keyword count
        try:
            url = f"{self.BASE_URL}/dataforseo_labs/google/domain_rank_overview/live"
            payload = [{
                "target": domain,
                "location_code": location_code,
            }]

            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if tasks and tasks[0].get("result"):
                items = tasks[0]["result"][0].get("items", [])
                if items:
                    item = items[0]
                    metrics["organic_etv"] = item.get("etv", 0) or 0
                    metrics["organic_keywords_count"] = item.get("count", 0) or 0
                    # Use organic rank if domain_rank is 0
                    if metrics["domain_rank"] == 0:
                        metrics["domain_rank"] = item.get("rank", 0) or 0
                    logger.info(f"📊 Organic for {domain}: traffic={metrics['organic_etv']}, keywords={metrics['organic_keywords_count']}")

        except Exception as e:
            logger.error(f"❌ Error getting organic metrics for {domain}: {e}")

        # If API returned no useful data, use estimates
        if (metrics["domain_rank"] == 0 and metrics["backlinks"] == 0 and
            metrics["organic_etv"] == 0 and metrics["organic_keywords_count"] == 0):
            logger.info(f"📊 API returned no data for {domain}, using estimates")
            return self._fallback_domain_metrics(domain)

        return metrics

    async def get_competitor_keywords(
        self,
        domain: str,
        location_code: int = 2792,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get keywords a competitor domain ranks for

        Args:
            domain: Competitor domain
            location_code: Geographic location
            limit: Number of keywords to return

        Returns:
            List of competitor keywords
        """
        if not self.login or not self.password:
            return []

        try:
            url = f"{self.BASE_URL}/dataforseo_labs/google/ranked_keywords/live"

            payload = [{
                "target": domain,
                "location_code": location_code,
                "limit": limit,
            }]

            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if not tasks or not tasks[0].get("result"):
                logger.warning(f"⚠️ No keyword results for {domain}")
                return []

            result_data = tasks[0]["result"][0] if tasks[0]["result"] else {}
            items = result_data.get("items") or []  # Handle None values

            results = []
            for item in items:
                se_results = item.get("ranked_serp_element", {}).get("serp_item", {})

                results.append({
                    "keyword": item.get("keyword_data", {}).get("keyword"),
                    "position": se_results.get("rank_group", 0),
                    "search_volume": item.get("keyword_data", {}).get("keyword_info", {}).get("search_volume", 0),
                    "cpc": item.get("keyword_data", {}).get("keyword_info", {}).get("cpc", 0),
                    "url": se_results.get("url"),
                })

            logger.info(f"📊 Got {len(results)} competitor keywords from DataForSEO")
            return results

        except Exception as e:
            logger.error(f"❌ Error getting competitor keywords: {e}")
            return []

    def _fallback_keyword_metrics(self, keywords: List[str]) -> List[Dict]:
        """Fallback keyword metrics"""
        logger.warning("⚠️ Using fallback keyword metrics")
        return [
            {
                "keyword": kw,
                "search_volume": 1000,
                "competition": 0.5,
                "cpc": 1.5,
                "competition_level": "MEDIUM",
            }
            for kw in keywords
        ]

    def _fallback_domain_metrics(self, domain: str = "") -> Dict:
        """Generate estimated domain metrics based on domain characteristics"""
        import hashlib

        logger.warning(f"⚠️ Using estimated metrics for {domain}")

        # Generate consistent pseudo-random values based on domain name
        # This ensures the same domain always gets the same estimated values
        domain_hash = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)

        # Known large domains get higher estimates
        large_domains = {
            "trendyol.com": {"rank": 85, "traffic": 45000000, "keywords": 2500000, "backlinks": 15000000},
            "hepsiburada.com": {"rank": 82, "traffic": 35000000, "keywords": 1800000, "backlinks": 12000000},
            "amazon.com": {"rank": 96, "traffic": 500000000, "keywords": 50000000, "backlinks": 100000000},
            "google.com": {"rank": 99, "traffic": 1000000000, "keywords": 100000000, "backlinks": 500000000},
            "n11.com": {"rank": 75, "traffic": 15000000, "keywords": 800000, "backlinks": 5000000},
            "gittigidiyor.com": {"rank": 70, "traffic": 8000000, "keywords": 500000, "backlinks": 3000000},
        }

        if domain in large_domains:
            data = large_domains[domain]
            return {
                "domain": domain,
                "domain_rank": data["rank"],
                "backlinks": data["backlinks"],
                "referring_domains": data["backlinks"] // 50,
                "organic_etv": data["traffic"],
                "organic_keywords_count": data["keywords"],
            }

        # For unknown domains, generate reasonable estimates based on hash
        base_rank = 20 + (domain_hash % 60)  # 20-80 range
        base_traffic = 10000 + (domain_hash % 990000)  # 10K-1M range
        base_keywords = 100 + (domain_hash % 9900)  # 100-10K range
        base_backlinks = 500 + (domain_hash % 49500)  # 500-50K range

        return {
            "domain": domain,
            "domain_rank": base_rank,
            "backlinks": base_backlinks,
            "referring_domains": base_backlinks // 10,
            "organic_etv": base_traffic,
            "organic_keywords_count": base_keywords,
        }

    async def get_regional_serp_positions(
        self,
        keyword: str,
        domains: List[str],
        province_codes: List[str] = None,
        depth: int = 100,
        batch_size: int = 3,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Dict[str, Optional[int]]]:
        """
        Get SERP positions for multiple domains across Turkish provinces.

        Args:
            keyword: Search query
            domains: List of domains to track (e.g., ["example.com", "competitor.com"])
            province_codes: List of province codes (e.g., ["34", "06", "35"]). If None, uses all provinces.
            depth: SERP depth to search (1-100)
            batch_size: Number of provinces to query in parallel
            delay_between_batches: Delay in seconds between batches to avoid rate limiting

        Returns:
            Dict mapping province_code to {domain: position, ...}
            Position is None if domain not found in top results.

        Example:
            {
                "34": {"example.com": 3, "competitor.com": 1},
                "06": {"example.com": 5, "competitor.com": None},
            }
        """
        if not self.login or not self.password:
            logger.info("DataForSEO credentials not configured, using fallback SERP data")
            return self._fallback_regional_serp(keyword, domains, province_codes)

        # Apply test mode filtering: only Istanbul (34), Ankara (06), Izmir (35)
        if settings.COMPETITOR_TEST_MODE:
            test_provinces = ["34", "06", "35"]
            if province_codes is None:
                province_codes = test_provinces
                logger.info(f"COMPETITOR_TEST_MODE active: limiting to {test_provinces}")
            else:
                original_count = len(province_codes)
                province_codes = [c for c in province_codes if c in test_provinces]
                if not province_codes:
                    province_codes = test_provinces
                logger.info(
                    f"COMPETITOR_TEST_MODE active: filtered {original_count} provinces down to {len(province_codes)}"
                )

        # Use all provinces if not specified (and not in test mode)
        if province_codes is None:
            province_codes = list(TURKEY_PROVINCE_LOCATION_CODES.keys())

        results: Dict[str, Dict[str, Optional[int]]] = {}
        error_count = 0

        # Process in batches to avoid rate limiting
        for i in range(0, len(province_codes), batch_size):
            batch = province_codes[i:i + batch_size]

            # Create tasks for parallel execution
            tasks = [
                self._get_serp_for_province(keyword, domains, code, depth)
                for code in batch
            ]

            # Execute batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_error_count = 0
            for code, result in zip(batch, batch_results):
                if isinstance(result, PaymentRequiredError):
                    logger.warning(
                        f"Payment error (402) for province {code}: DataForSEO account has insufficient credits. "
                        "Switching to fallback data for all provinces."
                    )
                    return self._fallback_regional_serp(keyword, domains, province_codes)
                elif isinstance(result, Exception):
                    exc_type = type(result).__name__
                    exc_msg = str(result) or "(no message)"
                    logger.error(
                        f"SERP request failed for province {code} "
                        f"[{exc_type}]: {exc_msg}"
                    )
                    error_count += 1
                    batch_error_count += 1
                    results[code] = {domain: None for domain in domains}
                else:
                    results[code] = result

            # Early bail-out: if the entire first batch failed, the API is likely
            # down or credentials are invalid. No point hammering remaining provinces.
            if i == 0 and batch_error_count == len(batch):
                logger.warning(
                    f"Entire first batch ({len(batch)} provinces) failed. "
                    "API appears unreachable or credentials invalid. Switching to fallback data."
                )
                return self._fallback_regional_serp(keyword, domains, province_codes)

            # Delay between batches
            if i + batch_size < len(province_codes):
                await asyncio.sleep(delay_between_batches)

        # If all calls failed, use fallback
        if error_count == len(province_codes):
            logger.warning(
                f"All {error_count} API calls failed. Using fallback data."
            )
            return self._fallback_regional_serp(keyword, domains, province_codes)

        logger.info(f"Got regional SERP positions for {len(results)} provinces ({error_count} errors)")
        return results

    async def _get_serp_for_province(
        self,
        keyword: str,
        domains: List[str],
        province_code: str,
        depth: int
    ) -> Dict[str, Optional[int]]:
        """
        Get SERP positions for domains in a specific province.
        Raises PaymentRequiredError for 402 errors so caller can switch to fallback.
        """
        location_code = TURKEY_PROVINCE_LOCATION_CODES.get(province_code)
        if not location_code:
            logger.warning(f"Unknown province code: {province_code}")
            return {domain: None for domain in domains}

        try:
            url = f"{self.BASE_URL}/serp/google/organic/live/advanced"

            payload = [{
                "keyword": keyword,
                "location_code": location_code,
                "language_code": "tr",
                "depth": depth,
            }]

            response = await self.client.post(
                url, json=payload, headers=self.headers, timeout=self.SERP_TIMEOUT,
            )

            # Check for payment errors before raise_for_status
            if response.status_code == 402:
                raise PaymentRequiredError("DataForSEO account has insufficient credits")

            response.raise_for_status()

            data = response.json()
            tasks = data.get("tasks", [])

            if not tasks or not tasks[0].get("result"):
                return {domain: None for domain in domains}

            items = tasks[0]["result"][0].get("items", [])

            # Find positions for each domain
            positions: Dict[str, Optional[int]] = {domain: None for domain in domains}

            for item in items:
                if item.get("type") != "organic":
                    continue

                item_domain = item.get("domain", "")

                for domain in domains:
                    # Check if domain matches (handle www. prefix)
                    if positions[domain] is None:
                        domain_lower = domain.lower()
                        item_domain_lower = item_domain.lower()

                        if (item_domain_lower == domain_lower or
                            item_domain_lower == f"www.{domain_lower}" or
                            f"www.{item_domain_lower}" == domain_lower or
                            item_domain_lower.endswith(f".{domain_lower}")):
                            positions[domain] = item.get("rank_group", 0)

            return positions

        except PaymentRequiredError:
            # Re-raise payment errors to be handled by caller
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                f"SERP HTTP error for province {province_code} "
                f"(location_code={location_code}): "
                f"status={e.response.status_code}, "
                f"body={e.response.text[:200]}"
            )
            raise
        except httpx.TimeoutException as e:
            logger.error(
                f"SERP timeout for province {province_code} "
                f"(location_code={location_code}): {type(e).__name__} "
                f"(timeout_config=connect:10s/read:80s)"
            )
            raise
        except Exception as e:
            exc_type = type(e).__name__
            exc_msg = str(e) or "(no message)"
            logger.error(
                f"SERP unexpected error for province {province_code} "
                f"(location_code={location_code}): [{exc_type}] {exc_msg}"
            )
            raise

    def _fallback_regional_serp(
        self,
        keyword: str,
        domains: List[str],
        province_codes: List[str] = None
    ) -> Dict[str, Dict[str, Optional[int]]]:
        """
        Generate fallback regional SERP data for development/testing.
        """
        import hashlib
        import random

        logger.warning("⚠️ Using fallback regional SERP data")

        if province_codes is None:
            province_codes = list(TURKEY_PROVINCE_LOCATION_CODES.keys())

        results: Dict[str, Dict[str, Optional[int]]] = {}

        for code in province_codes:
            # Generate consistent but varied positions based on hash
            seed = int(hashlib.md5(f"{keyword}:{code}".encode()).hexdigest()[:8], 16)
            random.seed(seed)

            positions: Dict[str, Optional[int]] = {}
            for idx, domain in enumerate(domains):
                # Each domain has a base position that varies by province
                domain_seed = int(hashlib.md5(f"{domain}:{code}".encode()).hexdigest()[:8], 16)
                random.seed(domain_seed)

                # 80% chance to appear in top 100
                if random.random() < 0.8:
                    positions[domain] = random.randint(1, 50)
                else:
                    positions[domain] = None

            results[code] = positions

        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
