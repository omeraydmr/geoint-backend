"""
Agent Schemas for AI Assistant

Defines tools and actions the AI agent can use to interact with the platform.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class AgentTool(str, Enum):
    """Available tools for the AI agent"""
    # Navigation
    NAVIGATE = "navigate"

    # GEOINT Module
    SELECT_KEYWORD = "select_keyword"
    CALCULATE_GEOINT = "calculate_geoint"
    CALCULATE_BUDGET = "calculate_budget"
    SHOW_PROVINCE = "show_province"

    # Keywords Module
    CREATE_KEYWORD = "create_keyword"
    ANALYZE_KEYWORD = "analyze_keyword"

    # Strategies Module
    CREATE_STRATEGY = "create_strategy"
    VIEW_STRATEGY = "view_strategy"
    GENERATE_AI_CONTENT = "generate_ai_content"

    # Competitors Module
    ADD_COMPETITOR = "add_competitor"
    ANALYZE_COMPETITOR = "analyze_competitor"
    COMPARE_COMPETITORS = "compare_competitors"

    # General
    SUGGEST_ACTIONS = "suggest_actions"
    SHOW_DATA = "show_data"


class AgentAction(BaseModel):
    """An action to be executed by the frontend"""
    tool: AgentTool = Field(..., description="The tool/action to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class AgentContext(BaseModel):
    """Context information sent with each agent request"""
    current_page: str = Field(default="/dashboard", description="Current page path")
    selected_keyword_id: Optional[str] = Field(None, description="Currently selected keyword ID")
    selected_keyword_name: Optional[str] = Field(None, description="Currently selected keyword name")
    keywords_list: List[Dict[str, str]] = Field(default_factory=list, description="User's keywords")
    selected_competitor_id: Optional[str] = Field(None, description="Currently selected competitor ID")
    selected_strategy_id: Optional[str] = Field(None, description="Currently selected strategy ID")


class AgentChatRequest(BaseModel):
    """Request for agent chat endpoint"""
    message: str = Field(..., description="User message")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Conversation history")
    context: AgentContext = Field(default_factory=AgentContext, description="Current context")


class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint"""
    response: str = Field(..., description="Conversational response text")
    actions: List[AgentAction] = Field(default_factory=list, description="Actions to execute")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up prompt suggestions")


# Tool definitions for Claude
AGENT_TOOLS = [
    {
        "name": "navigate",
        "description": "Kullaniciyi bir sayfaya yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "string",
                    "description": "Hedef sayfa yolu. Gecerli degerler: /dashboard, /geoint/map, /geoint/overview, /geoint/regions, /geoint/budget, /keywords, /strategies, /competitors, /competitors/compare, /settings"
                }
            },
            "required": ["page"]
        }
    },
    {
        "name": "select_keyword",
        "description": "Bir anahtar kelime secer. ID veya isim ile secim yapilabilir",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword_id": {
                    "type": "string",
                    "description": "Anahtar kelime ID'si"
                },
                "keyword_name": {
                    "type": "string",
                    "description": "Anahtar kelime ismi (ID bilinmiyorsa)"
                }
            }
        }
    },
    {
        "name": "calculate_geoint",
        "description": "Secili anahtar kelime icin GEOINT skorlarini hesaplar. Oncesinde bir kelime secili olmali",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "calculate_budget",
        "description": "Belirtilen butce miktari icin bolgesel dagitim onerisi hesaplar",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Butce miktari (TL)"
                }
            },
            "required": ["amount"]
        }
    },
    {
        "name": "show_province",
        "description": "Haritada belirtilen ili vurgular ve detaylarini gosterir",
        "input_schema": {
            "type": "object",
            "properties": {
                "province_name": {
                    "type": "string",
                    "description": "Il adi (ornek: Istanbul, Ankara, Izmir)"
                }
            },
            "required": ["province_name"]
        }
    },
    {
        "name": "create_keyword",
        "description": "Yeni bir anahtar kelime olusturma sayfasina yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Olusturulacak anahtar kelime (opsiyonel)"
                }
            }
        }
    },
    {
        "name": "analyze_keyword",
        "description": "Belirtilen anahtar kelime icin NLP analizi baslatir",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Analiz edilecek anahtar kelime"
                }
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "create_strategy",
        "description": "Yeni strateji olusturma sayfasina yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "view_strategy",
        "description": "Belirtilen stratejiyi goruntulemeye yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "Strateji ID'si"
                }
            },
            "required": ["strategy_id"]
        }
    },
    {
        "name": "add_competitor",
        "description": "Yeni rakip ekleme sayfasina yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Rakip domain adresi (opsiyonel)"
                }
            }
        }
    },
    {
        "name": "analyze_competitor",
        "description": "Belirtilen rakip icin analiz baslatir",
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_id": {
                    "type": "string",
                    "description": "Rakip ID'si"
                }
            },
            "required": ["competitor_id"]
        }
    },
    {
        "name": "compare_competitors",
        "description": "Rakip karsilastirma sayfasina yonlendirir",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "show_data",
        "description": "Chat icerisinde veri gosterir (kucuk veri setleri icin)",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "description": "Veri tipi: keywords, regions, stats"
                },
                "data": {
                    "type": "object",
                    "description": "Gosterilecek veri"
                }
            },
            "required": ["data_type"]
        }
    },
    {
        "name": "suggest_actions",
        "description": "Mevcut context icin uygun aksiyonlari onerir",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


# Quick action definitions based on page context
QUICK_ACTIONS_BY_PAGE = {
    "/dashboard": [
        {"label": "GEOINT'e Git", "prompt": "GEOINT haritasini goster"},
        {"label": "Strateji Olustur", "prompt": "Yeni strateji olusturmak istiyorum"},
        {"label": "Rakipleri Gor", "prompt": "Rakiplerimi goster"}
    ],
    "/geoint": [
        {"label": "Kelime Sec", "prompt": "Anahtar kelime secmek istiyorum"},
        {"label": "GEOINT Hesapla", "prompt": "GEOINT skorlarini hesapla"},
        {"label": "Butce Oner", "prompt": "Butce dagitim onerisi ver"}
    ],
    "/geoint/map": [
        {"label": "En Iyi Bolgeler", "prompt": "En yuksek skorlu illeri goster"},
        {"label": "Butce Dagit", "prompt": "Butce dagitimi yap"},
        {"label": "Trend Analizi", "prompt": "Trend analizini goster"}
    ],
    "/keywords": [
        {"label": "Kelime Ekle", "prompt": "Yeni anahtar kelime ekle"},
        {"label": "Analiz Et", "prompt": "Secili kelimeyi analiz et"},
        {"label": "GEOINT'e Git", "prompt": "Bu kelime icin GEOINT'e git"}
    ],
    "/strategies": [
        {"label": "Strateji Olustur", "prompt": "Yeni strateji olustur"},
        {"label": "Ilerleme Goster", "prompt": "Strateji ilerlemesini goster"},
        {"label": "AI Icerik Uret", "prompt": "AI ile icerik uret"}
    ],
    "/competitors": [
        {"label": "Rakip Ekle", "prompt": "Yeni rakip ekle"},
        {"label": "Karsilastir", "prompt": "Rakipleri karsilastir"},
        {"label": "Analiz Et", "prompt": "Rakip analizi yap"}
    ]
}
