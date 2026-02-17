"""
NLP endpoints for Turkish language processing
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.services.nlp.turkish_processor import TurkishNLPProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nlp", tags=["nlp"])


# Request/Response models
class KeywordAnalysisRequest(BaseModel):
    """Request for keyword NLP analysis"""
    keyword_id: str = Field(..., description="Keyword ID")
    keyword: str = Field(..., description="Keyword text")


class KeywordAnalysisResponse(BaseModel):
    """Response from keyword NLP analysis"""
    keyword_id: str
    keyword: str
    root_form: str
    intent: str
    nlp_metadata: Dict[str, Any]


class TextAnalysisRequest(BaseModel):
    """Request for general text analysis"""
    text: str = Field(..., description="Text to analyze")
    language: str = Field(default="tr", description="Language code")


class TextAnalysisResponse(BaseModel):
    """Response from text analysis"""
    language: str
    sentiment: str
    sentiment_score: float
    entities: List[Dict[str, Any]]
    keywords: List[str]
    topics: List[str]


class IntentClassificationRequest(BaseModel):
    """Request for intent classification"""
    queries: List[str] = Field(..., description="Search queries to classify")


class IntentClassificationResponse(BaseModel):
    """Response from intent classification"""
    results: List[Dict[str, Any]]


@router.post("/keyword/analyze", response_model=KeywordAnalysisResponse)
async def analyze_keyword(
    request: KeywordAnalysisRequest,
    authorization: Optional[str] = Header(None)
) -> KeywordAnalysisResponse:
    """
    Analyze Turkish keyword using NLP

    Extracts:
    - Root form (morphological analysis)
    - Search intent (informational, navigational, transactional, commercial)
    - Semantic variations
    - Related terms
    """
    try:
        # Extract JWT token
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        # Initialize Turkish NLP processor
        processor = TurkishNLPProcessor()

        # Perform NLP analysis
        analysis = await processor.analyze_keyword(request.keyword)

        return KeywordAnalysisResponse(
            keyword_id=request.keyword_id,
            keyword=request.keyword,
            root_form=analysis["root_form"],
            intent=analysis["intent"],
            nlp_metadata=analysis["metadata"]
        )

    except Exception as e:
        logger.error(f"Error analyzing keyword: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text/analyze", response_model=TextAnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    authorization: Optional[str] = Header(None)
) -> TextAnalysisResponse:
    """
    Comprehensive Turkish text analysis

    Performs:
    - Sentiment analysis
    - Named entity recognition
    - Keyword extraction
    - Topic modeling
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        processor = TurkishNLPProcessor()
        analysis = await processor.analyze_text(request.text, request.language)

        return TextAnalysisResponse(
            language=analysis["language"],
            sentiment=analysis["sentiment"],
            sentiment_score=analysis["sentiment_score"],
            entities=analysis["entities"],
            keywords=analysis["keywords"],
            topics=analysis["topics"]
        )

    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intent/classify", response_model=IntentClassificationResponse)
async def classify_intent(
    request: IntentClassificationRequest,
    authorization: Optional[str] = Header(None)
) -> IntentClassificationResponse:
    """
    Classify search intent for Turkish queries

    Intent categories:
    - informational: User wants information
    - navigational: User wants to find a specific page
    - transactional: User wants to perform action/purchase
    - commercial: User is researching before purchase
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        processor = TurkishNLPProcessor()
        results = []

        for query in request.queries:
            intent_data = await processor.classify_intent(query)
            results.append({
                "query": query,
                "intent": intent_data["intent"],
                "confidence": intent_data["confidence"],
                "intent_scores": intent_data["scores"]
            })

        return IntentClassificationResponse(results=results)

    except Exception as e:
        logger.error(f"Error classifying intent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment/batch")
async def batch_sentiment_analysis(
    texts: List[str],
    authorization: Optional[str] = Header(None)
) -> List[Dict[str, Any]]:
    """
    Batch sentiment analysis for Turkish text
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        processor = TurkishNLPProcessor()
        results = []

        for text in texts:
            sentiment_data = await processor.analyze_sentiment(text)
            results.append({
                "text": text[:100],  # First 100 chars
                "sentiment": sentiment_data["sentiment"],
                "score": sentiment_data["score"],
                "confidence": sentiment_data["confidence"]
            })

        return results

    except Exception as e:
        logger.error(f"Error in batch sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/extract")
async def extract_entities(
    text: str,
    entity_types: Optional[List[str]] = None,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extract named entities from Turkish text

    Entity types:
    - PERSON: People names
    - ORGANIZATION: Company, agency names
    - LOCATION: Cities, countries, regions
    - DATE: Dates and time expressions
    - MONEY: Monetary values
    - PRODUCT: Product names
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        processor = TurkishNLPProcessor()
        entities = await processor.extract_entities(text, entity_types)

        return {
            "text": text,
            "entities": entities,
            "entity_count": len(entities)
        }

    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords/extract")
async def extract_keywords(
    text: str,
    max_keywords: int = 10,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extract important keywords from Turkish text
    """
    try:
        token = authorization.replace("Bearer ", "") if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization required")

        processor = TurkishNLPProcessor()
        keywords = await processor.extract_keywords(text, max_keywords)

        return {
            "keywords": keywords,
            "keyword_count": len(keywords)
        }

    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
