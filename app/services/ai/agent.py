"""
AI Agent Service

Provides intelligent agent capabilities that can understand natural language,
navigate pages, select data, and execute actions across the STRATYON platform.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.schemas.agent import (
    AgentContext,
    AgentAction,
    AgentTool,
    AGENT_TOOLS,
    QUICK_ACTIONS_BY_PAGE
)

logger = logging.getLogger(__name__)


class AgentService:
    """
    AI Agent Service for STRATYON

    Uses Claude to interpret user intent and select appropriate tools/actions.
    """

    SYSTEM_PROMPT = """Sen STRATYON platformunun akilli AI asistanisin.
Kullanicilarin dogal dil komutlarini anlayip platform uzerinde islemler yapabilirsin.

GOREVLERIN:
1. Kullanicinin niyetini anla
2. Uygun tool'lari sec ve cagir
3. Kisa ve oz Turkce yanit ver
4. Kullaniciyi dogru sayfalara yonlendir

PLATFORM MODULLERI:
- GEOINT: Cografi istihbarat, il bazli pazar analizi, isi haritasi
- Keywords (Anahtar Kelimeler): Anahtar kelime takibi ve analizi
- Strategies (Stratejiler): 90 gunluk pazarlama stratejileri
- Competitors (Rakipler): Rakip web sitesi analizi
- Dashboard: Genel bakis paneli

ONEMLI KURALLAR:
1. Kullanici bir islem istediginde mutlaka uygun tool'u cagir
2. Sayfaya yonlendirme gerektiginde navigate tool'unu kullan
3. Yanit her zaman Turkce olsun
4. Cok uzun aciklamalar yapma, kisa ve oz ol
5. Detayli veri isteginde sayfaya yonlendir, chat'te gosterme
6. Kullanicinin mevcut sayfasini ve secili verilerini dikkate al
7. IL ADI GECTIGINDE MUTLAKA show_province TOOL'UNU KULLAN!

SAYFA YOLLARI:
- /dashboard - Ana panel
- /geoint/map - GEOINT isi haritasi
- /geoint/overview - GEOINT genel bakis
- /geoint/regions - Bolge listesi
- /geoint/budget - Butce dagitimi
- /keywords - Anahtar kelimeler
- /strategies - Stratejiler
- /competitors - Rakipler
- /competitors/compare - Rakip karsilastirma
- /settings - Ayarlar

TURKIYE ILLERI (show_province icin kullan):
Istanbul, Ankara, Izmir, Bursa, Antalya, Adana, Konya, Gaziantep, Mersin, Diyarbakir,
Kayseri, Eskisehir, Samsun, Denizli, Sanliurfa, Malatya, Trabzon, Erzurum, Van, Manisa,
Balikesir, Kocaeli, Sakarya, Tekirdag, Mugla, Aydin, Hatay, Kahramanmaras, Mardin, Batman,
Elazig, Sivas, Afyonkarahisar, Kutahya, Usak, Isparta, Burdur, Zonguldak, Karabuk, Bartin,
Kastamonu, Cankiri, Corum, Amasya, Tokat, Ordu, Giresun, Rize, Artvin, Gumushane, Bayburt,
Erzincan, Tunceli, Bingol, Mus, Bitlis, Siirt, Sirnak, Hakkari, Agri, Igdir, Kars, Ardahan,
Nigde, Aksaray, Nevsehir, Kirsehir, Yozgat, Karaman, Kirikkale, Bilecik, Bolu, Duzce, Yalova,
Edirne, Kirklareli, Canakkale, Kilis, Osmaniye, Adiyaman

ORNEK TOOL KULLANIMI:
- "Istanbul GEOINT skoru nedir?" -> MUTLAKA show_province tool'unu cagir: {"province_name": "Istanbul"} ve yanit: "Istanbul ilinin ilce bazli GEOINT skorlarini gosteriyorum."
- "Ankara'yi haritada goster" -> show_province: {"province_name": "Ankara"} ve yanit: "Ankara ilinin ilcelerini haritada gosteriyorum."
- "Izmir icin analiz" -> show_province: {"province_name": "Izmir"} ve yanit: "Izmir ilinin ilce bazli analizini gosteriyorum."
- "GEOINT skorlarini goster" -> navigate: {"page": "/geoint/map"}
- "50000 TL butcem var" -> calculate_budget: {"amount": 50000}
- "Yeni kelime ekle" -> navigate: {"page": "/keywords"}

ONEMLI: show_province tool'u kullanildiginda harita otomatik olarak ilin ilcelerini (district view) gosterir.
"""

    def __init__(self):
        self.tools = AGENT_TOOLS

    async def process_message(
        self,
        message: str,
        history: List[Dict[str, str]],
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Process a user message and return response with actions

        Args:
            message: User's message
            history: Conversation history
            context: Current context (page, selected items, etc.)

        Returns:
            Dict with response, actions, and suggestions
        """
        try:
            if settings.ANTHROPIC_API_KEY:
                return await self._process_with_claude(message, history, context)
            else:
                return self._fallback_response(message, context)
        except Exception as e:
            logger.error(f"Agent processing error: {e}")
            return {
                "response": "Bir hata olustu. Lutfen tekrar deneyin.",
                "actions": [],
                "suggestions": []
            }

    async def _process_with_claude(
        self,
        message: str,
        history: List[Dict[str, str]],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Process message using Claude with tool use"""
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            # Build context message
            context_info = self._build_context_info(context)

            # Format messages
            messages = []
            for msg in history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})

            # Add current message with context
            user_message = f"{context_info}\n\nKullanici mesaji: {message}"
            messages.append({"role": "user", "content": user_message})

            # Call Claude with tools
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                temperature=0.3,
                system=self.SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages
            )

            # Process response
            return self._process_claude_response(response, context)

        except Exception as e:
            logger.error(f"Claude agent error: {e}")
            return self._fallback_response(message, context)

    def _build_context_info(self, context: AgentContext) -> str:
        """Build context information string for Claude"""
        parts = [f"Mevcut sayfa: {context.current_page}"]

        if context.selected_keyword_id:
            parts.append(f"Secili anahtar kelime ID: {context.selected_keyword_id}")
        if context.selected_keyword_name:
            parts.append(f"Secili anahtar kelime: {context.selected_keyword_name}")

        if context.keywords_list:
            keyword_names = [k.get("keyword", k.get("name", "")) for k in context.keywords_list[:10]]
            parts.append(f"Kullanicinin anahtar kelimeleri: {', '.join(keyword_names)}")

        if context.selected_competitor_id:
            parts.append(f"Secili rakip ID: {context.selected_competitor_id}")

        if context.selected_strategy_id:
            parts.append(f"Secili strateji ID: {context.selected_strategy_id}")

        return "\n".join(parts)

    def _process_claude_response(
        self,
        response: Any,
        context: AgentContext
    ) -> Dict[str, Any]:
        """Process Claude's response and extract text and tool calls"""
        text_response = ""
        actions = []

        for block in response.content:
            if block.type == "text":
                text_response = block.text
            elif block.type == "tool_use":
                action = self._convert_tool_use_to_action(block)
                if action:
                    actions.append(action)

        # If stop reason is tool_use, we may need to continue
        # For now, just return what we have

        # Generate suggestions based on context and actions
        suggestions = self._generate_suggestions(context, actions)

        return {
            "response": text_response or "Islem tamamlandi.",
            "actions": [a.model_dump() for a in actions],
            "suggestions": suggestions
        }

    def _convert_tool_use_to_action(self, tool_use: Any) -> Optional[AgentAction]:
        """Convert Claude's tool_use block to AgentAction"""
        try:
            tool_name = tool_use.name
            tool_input = tool_use.input or {}

            # Map tool name to AgentTool enum
            tool_mapping = {
                "navigate": AgentTool.NAVIGATE,
                "select_keyword": AgentTool.SELECT_KEYWORD,
                "calculate_geoint": AgentTool.CALCULATE_GEOINT,
                "calculate_budget": AgentTool.CALCULATE_BUDGET,
                "show_province": AgentTool.SHOW_PROVINCE,
                "create_keyword": AgentTool.CREATE_KEYWORD,
                "analyze_keyword": AgentTool.ANALYZE_KEYWORD,
                "create_strategy": AgentTool.CREATE_STRATEGY,
                "view_strategy": AgentTool.VIEW_STRATEGY,
                "add_competitor": AgentTool.ADD_COMPETITOR,
                "analyze_competitor": AgentTool.ANALYZE_COMPETITOR,
                "compare_competitors": AgentTool.COMPARE_COMPETITORS,
                "show_data": AgentTool.SHOW_DATA,
                "suggest_actions": AgentTool.SUGGEST_ACTIONS
            }

            if tool_name in tool_mapping:
                return AgentAction(
                    tool=tool_mapping[tool_name],
                    parameters=tool_input
                )

            return None
        except Exception as e:
            logger.error(f"Error converting tool use: {e}")
            return None

    def _generate_suggestions(
        self,
        context: AgentContext,
        actions: List[AgentAction]
    ) -> List[str]:
        """Generate follow-up suggestions based on context and actions"""
        suggestions = []

        # Get base page for suggestions
        base_page = context.current_page.split("/")[1] if "/" in context.current_page else "dashboard"
        page_key = f"/{base_page}"

        # Check if we're navigating somewhere
        target_page = None
        for action in actions:
            if action.tool == AgentTool.NAVIGATE:
                target_page = action.parameters.get("page", "")
                page_key = target_page.rsplit("/", 1)[0] if "/" in target_page else target_page

        # Get quick actions for the relevant page
        page_actions = QUICK_ACTIONS_BY_PAGE.get(page_key, [])

        # Add context-aware suggestions
        if page_key in ["/geoint", "/geoint/map"]:
            if not context.selected_keyword_id:
                suggestions.append("Anahtar kelime secmek istiyorum")
            else:
                suggestions.append("GEOINT skorlarini hesapla")
                suggestions.append("Butce dagitimi yap")
                suggestions.append("En iyi bolgeleri goster")

        elif page_key == "/keywords":
            suggestions.append("Yeni kelime ekle")
            suggestions.append("Kelime analizi yap")
            suggestions.append("GEOINT'e git")

        elif page_key == "/strategies":
            suggestions.append("Yeni strateji olustur")
            suggestions.append("Strateji detaylarini goster")

        elif page_key == "/competitors":
            suggestions.append("Rakip ekle")
            suggestions.append("Rakipleri karsilastir")

        # Limit suggestions
        return suggestions[:4]

    def _fallback_response(
        self,
        message: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """Provide fallback response when Claude is not available"""
        message_lower = message.lower()
        actions = []
        response = ""

        # Turkish province names for matching
        provinces = [
            "istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya",
            "gaziantep", "mersin", "diyarbakir", "kayseri", "eskisehir", "samsun",
            "denizli", "sanliurfa", "malatya", "trabzon", "erzurum", "van", "manisa",
            "balikesir", "kocaeli", "sakarya", "tekirdag", "mugla", "aydin", "hatay",
            "kahramanmaras", "mardin", "batman", "elazig", "sivas", "afyonkarahisar",
            "kutahya", "usak", "isparta", "burdur", "zonguldak", "karabuk", "bartin",
            "kastamonu", "cankiri", "corum", "amasya", "tokat", "ordu", "giresun",
            "rize", "artvin", "gumushane", "bayburt", "erzincan", "tunceli", "bingol",
            "mus", "bitlis", "siirt", "sirnak", "hakkari", "agri", "igdir", "kars",
            "ardahan", "nigde", "aksaray", "nevsehir", "kirsehir", "yozgat", "karaman",
            "kirikkale", "bilecik", "bolu", "duzce", "yalova", "edirne", "kirklareli",
            "canakkale", "kilis", "osmaniye", "adiyaman"
        ]

        # Check for province name in message
        found_province = None
        for province in provinces:
            if province in message_lower:
                found_province = province.capitalize()
                break

        # If a province is mentioned, use show_province
        if found_province:
            actions.append(AgentAction(tool=AgentTool.SHOW_PROVINCE, parameters={"province_name": found_province}))
            response = f"{found_province} ilinin ilce bazli GEOINT skorlarini gosteriyorum."

        # Simple keyword matching for common commands
        elif any(word in message_lower for word in ["geoint", "harita", "skor", "bolge"]):
            actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/geoint/map"}))
            response = "GEOINT haritasina yonlendiriyorum."

        elif any(word in message_lower for word in ["kelime", "keyword", "anahtar"]):
            if "ekle" in message_lower or "yeni" in message_lower:
                actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/keywords"}))
                response = "Anahtar kelimeler sayfasina yonlendiriyorum."
            else:
                actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/keywords"}))
                response = "Anahtar kelimeler sayfasina yonlendiriyorum."

        elif any(word in message_lower for word in ["strateji", "plan"]):
            actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/strategies"}))
            response = "Stratejiler sayfasina yonlendiriyorum."

        elif any(word in message_lower for word in ["rakip", "competitor"]):
            if "karsilastir" in message_lower:
                actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/competitors/compare"}))
                response = "Rakip karsilastirma sayfasina yonlendiriyorum."
            else:
                actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/competitors"}))
                response = "Rakipler sayfasina yonlendiriyorum."

        elif any(word in message_lower for word in ["butce", "bütçe", "dagit"]):
            actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/geoint/budget"}))
            response = "Butce dagitimi sayfasina yonlendiriyorum."

        elif any(word in message_lower for word in ["dashboard", "ana sayfa", "anasayfa", "panel"]):
            actions.append(AgentAction(tool=AgentTool.NAVIGATE, parameters={"page": "/dashboard"}))
            response = "Ana panele yonlendiriyorum."

        else:
            response = "Size nasil yardimci olabilirim? GEOINT, anahtar kelimeler, stratejiler veya rakip analizi konularinda sorularinizi yanıtlayabilirim."

        suggestions = self._generate_suggestions(context, actions)

        return {
            "response": response,
            "actions": [a.model_dump() for a in actions],
            "suggestions": suggestions
        }
