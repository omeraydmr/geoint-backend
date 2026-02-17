"""
TKGM (Tapu ve Kadastro Genel Müdürlüğü) API Client

Turkish Land Registry and Cadastre - provides official geographic data
"""
from typing import List, Dict, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


class TKGMClient:
    """
    Client for TKGM (Turkish Land Registry) API

    Provides access to official administrative boundaries:
    - Provinces (İller)
    - Districts (İlçeler)
    - Neighborhoods (Mahalleler)
    """

    BASE_URL = "https://cbsapi.tkgm.gov.tr/megsiswebapi.v3/api"

    def __init__(self, timeout: int = 30):
        self.client = httpx.AsyncClient(timeout=timeout)
        self.timeout = timeout

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    async def get_provinces(self) -> List[Dict]:
        """
        Get list of all Turkish provinces

        Returns:
            List of province dicts with keys: il_kodu, il_adi, etc.
        """
        try:
            response = await self.client.get(f"{self.BASE_URL}/idariYapi/ilListe")
            response.raise_for_status()
            data = response.json()

            logger.info(f"📍 Got {len(data)} provinces from TKGM")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching provinces from TKGM: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    async def get_districts(self, province_id: int) -> List[Dict]:
        """
        Get districts for a specific province

        Args:
            province_id: Province ID (e.g., 34 for Istanbul)

        Returns:
            List of district dicts
        """
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/idariYapi/ilceListe/{province_id}"
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"📍 Got {len(data)} districts for province {province_id}")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching districts for province {province_id}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    async def get_neighborhoods(self, district_id: int) -> List[Dict]:
        """
        Get neighborhoods for a specific district

        Args:
            district_id: District ID

        Returns:
            List of neighborhood dicts
        """
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/idariYapi/mahalleListe/{district_id}"
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"📍 Got {len(data)} neighborhoods for district {district_id}")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching neighborhoods for district {district_id}: {e}")
            raise

    async def get_all_districts(self) -> List[Dict]:
        """
        Get all districts from all provinces

        Returns:
            List of all districts
        """
        provinces = await self.get_provinces()
        all_districts = []

        for province in provinces:
            province_id = province.get('il_kodu') or province.get('id')
            if province_id:
                try:
                    districts = await self.get_districts(province_id)
                    all_districts.extend(districts)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get districts for province {province_id}: {e}")

        logger.info(f"📍 Total districts collected: {len(all_districts)}")
        return all_districts

    async def get_province_by_code(self, province_code: str) -> Optional[Dict]:
        """
        Get province details by code

        Args:
            province_code: Province code (e.g., "34" for Istanbul)

        Returns:
            Province dict or None
        """
        provinces = await self.get_provinces()
        code_int = int(province_code)

        for province in provinces:
            if province.get('il_kodu') == code_int or province.get('id') == code_int:
                return province

        return None

    async def search_district(
        self,
        district_name: str,
        province_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for districts by name

        Args:
            district_name: District name to search for
            province_id: Optional province filter

        Returns:
            List of matching districts
        """
        if province_id:
            districts = await self.get_districts(province_id)
        else:
            districts = await self.get_all_districts()

        # Case-insensitive search
        district_name_lower = district_name.lower()
        matches = [
            d for d in districts
            if district_name_lower in str(d.get('ilce_adi', '')).lower()
        ]

        return matches

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
