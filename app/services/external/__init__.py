"""External API clients"""
from app.services.external.tkgm import TKGMClient
from app.services.external.dataforseo import DataForSEOClient

__all__ = ["TKGMClient", "DataForSEOClient"]
