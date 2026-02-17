"""
AI Strategy Generator Service

Generates 90-day strategic marketing plans using LLMs (GPT-4 or Claude)
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging
import re

from app.models.strategy import Strategy, StrategyWeek, StrategyTask


def extract_json_from_text(text: str) -> dict:
    """Extract JSON object from text that may contain extra content"""
    # Try direct parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block between ```json and ```
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object by matching braces
    start = text.find('{')
    if start != -1:
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Could not extract valid JSON", text, 0)
from app.models.keyword import Keyword
from app.models.geo import GEOINTScore
from app.core.config import settings

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """
    AI-powered 90-day strategy generator

    Uses GPT-4o-mini or Claude Haiku to generate strategic marketing plans
    based on GEOINT data, keywords, and market insights.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_strategy(
        self,
        user_id: str,
        name: str,
        primary_goal: str,
        target_keywords: List[str],
        total_budget: Optional[float] = None,
        industry: Optional[str] = None,
        target_audience: Optional[str] = None
    ) -> Strategy:
        """
        Generate a complete 90-day strategy

        Args:
            user_id: User UUID
            name: Strategy name
            primary_goal: Primary business goal
            target_keywords: List of target keywords
            total_budget: Total budget in TL
            industry: Industry/vertical
            target_audience: Target audience description

        Returns:
            Strategy object with weekly breakdown
        """
        logger.info(f"🎯 Generating strategy: {name}")

        # Gather context data
        context = await self._gather_context(user_id, target_keywords)

        # Generate strategy content with LLM
        strategy_content = await self._generate_with_llm(
            primary_goal=primary_goal,
            context=context,
            budget=total_budget,
            industry=industry,
            target_audience=target_audience
        )

        # Create strategy record
        strategy = Strategy(
            user_id=user_id,
            name=name,
            primary_goal=primary_goal,
            target_keywords=target_keywords,
            target_regions=context.get("top_regions", []),
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=90),
            total_budget=total_budget,
            executive_summary=strategy_content.get("executive_summary"),
            opportunities=strategy_content.get("opportunities"),
            threats=strategy_content.get("threats"),
            kpi_targets=strategy_content.get("kpi_targets"),
            generated_by_model=strategy_content.get("model"),
            generation_timestamp=datetime.utcnow()
        )

        self.db.add(strategy)
        await self.db.flush()

        # Create weekly plan
        await self._create_weekly_plan(strategy, strategy_content.get("weeks", []))

        await self.db.commit()

        logger.info(f"✅ Strategy generated: {strategy.id}")
        return strategy

    async def _gather_context(self, user_id: str, target_keywords: List[str]) -> Dict:
        """
        Gather context data for strategy generation

        Collects GEOINT scores, keyword metrics, and market insights
        """
        context = {
            "keywords": [],
            "top_regions": [],
            "geoint_insights": [],
        }

        # Get keyword data
        for kw_text in target_keywords:
            result = await self.db.execute(
                select(Keyword).where(
                    Keyword.user_id == user_id,
                    Keyword.keyword == kw_text
                )
            )
            keyword = result.scalar_one_or_none()

            if keyword:
                # Get top GEOINT scores for this keyword
                scores_result = await self.db.execute(
                    select(GEOINTScore)
                    .where(GEOINTScore.keyword_id == keyword.id)
                    .order_by(GEOINTScore.geoint_score.desc())
                    .limit(5)
                )
                scores = scores_result.scalars().all()

                context["keywords"].append({
                    "keyword": keyword.keyword,
                    "intent": keyword.intent,
                    "search_volume": keyword.avg_monthly_searches,
                    "top_score": scores[0].geoint_score if scores else 0,
                })

                # Add top regions
                for score in scores:
                    if str(score.region_id) not in context["top_regions"]:
                        context["top_regions"].append(str(score.region_id))
                        context["geoint_insights"].append({
                            "region_id": str(score.region_id),
                            "keyword": keyword.keyword,
                            "score": score.geoint_score,
                            "trend": score.trend_direction,
                        })

        return context

    async def _generate_with_llm(
        self,
        primary_goal: str,
        context: Dict,
        budget: Optional[float],
        industry: Optional[str],
        target_audience: Optional[str]
    ) -> Dict:
        """
        Generate strategy using LLM (Claude)

        Returns structured strategy content
        """
        # Use Claude if API key is available
        if settings.ANTHROPIC_API_KEY:
            return await self._generate_with_claude(
                primary_goal, context, budget, industry, target_audience
            )

        # Fallback to template-based strategy
        else:
            logger.warning("⚠️ No Claude API key configured, using template")
            return self._generate_template_strategy(primary_goal, context, budget)

    async def _generate_with_claude(
        self,
        primary_goal: str,
        context: Dict,
        budget: Optional[float],
        industry: Optional[str],
        target_audience: Optional[str]
    ) -> Dict:
        """Generate with Anthropic Claude"""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt = self._build_strategy_prompt(
                primary_goal, context, budget, industry, target_audience
            )

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text

            # Parse JSON response (with extraction for robustness)
            strategy_data = extract_json_from_text(content)
            strategy_data["model"] = "claude-3-haiku"

            logger.info("✅ Strategy generated with Claude")
            return strategy_data

        except Exception as e:
            logger.error(f"❌ Claude generation failed: {e}")
            return self._generate_template_strategy(primary_goal, context, budget)

    def _build_strategy_prompt(
        self,
        primary_goal: str,
        context: Dict,
        budget: Optional[float],
        industry: Optional[str],
        target_audience: Optional[str]
    ) -> str:
        """Build LLM prompt for strategy generation"""
        budget_str = f"{budget:,.0f} TL" if budget else "Belirtilmedi"

        return f"""90 günlük dijital pazarlama stratejisi oluştur.

**Hedef:** {primary_goal}

**Bütçe:** {budget_str}

**Sektör:** {industry or 'Belirtilmedi'}

**Hedef Kitle:** {target_audience or 'Belirtilmedi'}

**Anahtar Kelimeler ve GEOINT İçgörüleri:**
{json.dumps(context, indent=2, ensure_ascii=False)}

**İstenen Çıktı Formatı (JSON):**
{{
    "executive_summary": "2-3 paragraf özet",
    "opportunities": [
        {{"title": "Fırsat başlığı", "description": "Açıklama", "priority": "HIGH/MEDIUM/LOW"}}
    ],
    "threats": [
        {{"title": "Tehdit başlığı", "description": "Açıklama", "impact": "HIGH/MEDIUM/LOW"}}
    ],
    "kpi_targets": {{
        "traffic_increase": "Yüzde hedefi",
        "conversion_rate": "Yüzde hedefi",
        "roi": "Hedef ROI"
    }},
    "weeks": [
        {{
            "week_number": 1,
            "focus_area": "Hafta odak alanı",
            "objectives": ["Hedef 1", "Hedef 2"],
            "tasks": [
                {{
                    "title": "Görev başlığı",
                    "description": "Görev açıklaması",
                    "category": "content/seo/ads/social",
                    "priority": "HIGH/MEDIUM/LOW",
                    "estimated_hours": 10
                }}
            ]
        }}
    ]
}}

Sadece JSON formatında yanıt ver. Türkiye pazarına özel öneriler sun."""

    def _generate_template_strategy(
        self,
        primary_goal: str,
        context: Dict,
        budget: Optional[float]
    ) -> Dict:
        """Generate basic template-based strategy (fallback)"""
        logger.warning("⚠️ Using template-based strategy generation")

        weeks = []
        for i in range(13):  # 13 weeks = ~90 days
            week_num = i + 1

            # Determine focus area based on week
            if week_num <= 2:
                focus = "Kurulum ve Analiz"
            elif week_num <= 6:
                focus = "İçerik ve SEO"
            elif week_num <= 10:
                focus = "Reklamlar ve Dönüşüm"
            else:
                focus = "Optimizasyon ve Ölçeklendirme"

            weeks.append({
                "week_number": week_num,
                "focus_area": focus,
                "objectives": [
                    f"Hafta {week_num} hedefi 1",
                    f"Hafta {week_num} hedefi 2"
                ],
                "tasks": [
                    {
                        "title": f"{focus} - Görev 1",
                        "description": "Görev açıklaması",
                        "category": "seo" if week_num <= 6 else "ads",
                        "priority": "MEDIUM",
                        "estimated_hours": 8
                    }
                ]
            })

        return {
            "executive_summary": f"90 günlük strateji: {primary_goal}",
            "opportunities": [
                {"title": "Fırsat 1", "description": "Açıklama", "priority": "high"}
            ],
            "threats": [
                {"title": "Tehdit 1", "description": "Açıklama", "impact": "medium"}
            ],
            "kpi_targets": {
                "traffic_increase": "100%",
                "conversion_rate": "5%",
                "roi": "300%"
            },
            "weeks": weeks,
            "model": "template"
        }

    async def _create_weekly_plan(self, strategy: Strategy, weeks_data: List[Dict]):
        """Create weekly breakdown and tasks"""
        for week_data in weeks_data:
            week_number = week_data.get("week_number", 1)

            # Calculate week dates
            week_start = strategy.start_date + timedelta(weeks=week_number - 1)
            week_end = week_start + timedelta(days=6)

            # Create week
            week = StrategyWeek(
                strategy_id=strategy.id,
                week_number=week_number,
                week_start_date=week_start,
                week_end_date=week_end,
                focus_area=week_data.get("focus_area"),
                objectives=week_data.get("objectives"),
                budget_allocated=strategy.total_budget / 13 if strategy.total_budget else None,
                completion_percentage=0
            )

            self.db.add(week)
            await self.db.flush()

            # Create tasks
            for task_data in week_data.get("tasks", []):
                # Normalize priority to uppercase for enum
                priority_str = task_data.get("priority", "MEDIUM").upper()

                task = StrategyTask(
                    week_id=week.id,
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    category=task_data.get("category"),
                    priority=priority_str,
                    estimated_hours=task_data.get("estimated_hours"),
                    estimated_cost=task_data.get("estimated_cost")
                )
                self.db.add(task)
