"""
AI Chatbot Service

Provides conversational AI capabilities using LLMs (GPT-4 or Claude)
"""
import logging
from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ChatbotService:
    """
    AI Chatbot Service for STRATYON
    """

    SYSTEM_PROMPT = """
    Sen STRATYON platformunun Yapay Zeka Asistanısın.
    STRATYON, Türkiye pazarı için stratejik pazarlama istihbaratı ve GEOINT (Coğrafi İstihbarat) platformudur.
    
    Görevlerin:
    1. Kullanıcılara dijital pazarlama stratejileri, SEO, rakip analizi ve reklam yönetimi konularında yardımcı olmak.
    2. GEOINT verilerini (bölgesel fırsatlar, trendler) anlamalarına yardımcı olmak.
    3. Platformun özelliklerini (Anahtar Kelime Araştırması, Rakip Takibi, Medya İzleme, AI Strateji) nasıl kullanacaklarını açıklamak.
    
    Tonun: Profesyonel, yardımsever, stratejik ve veriye dayalı.
    Dil: Türkçe (Kullanıcı başka bir dilde yazarsa o dilde yanıt ver).
    
    Özellikler Hakkında Bilgi:
    - GEOINT: İl ve ilçe bazında pazar fırsatlarını harita üzerinde gösterir.
    - Strateji Oluşturucu: 90 günlük detaylı pazarlama planı hazırlar.
    - Rakip Analizi: Rakiplerin SEO ve reklam performansını takip eder.
    
    Kısa ve öz yanıtlar ver. Madde işaretleri kullan.
    """

    def __init__(self):
        pass

    async def generate_response(self, message: str, history: List[Dict[str, str]] = []) -> str:
        """
        Generate a response to a user message
        """
        if settings.ANTHROPIC_API_KEY:
            return await self._chat_with_claude(message, history)
            
        else:
            return "Üzgünüm, şu anda AI servislerine erişemiyorum. Lütfen API anahtarlarını kontrol edin."

    async def _chat_with_claude(self, message: str, history: List[Dict[str, str]]) -> str:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            # Format history for Claude
            messages = []
            for msg in history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
            
            messages.append({"role": "user", "content": message})

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.7,
                system=self.SYSTEM_PROMPT,
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Claude chat error: {e}")
            return "Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
