"""
AI Strategy Refiner Service

Provides AI-powered analysis and refinement suggestions for strategies
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from app.models.strategy import Strategy, StrategyWeek, StrategyTask
from app.core.config import settings

logger = logging.getLogger(__name__)


class StrategyRefiner:
    """
    AI-powered strategy refinement and suggestions

    Uses GPT-4o-mini or Claude to provide:
    - Progress analysis
    - Improvement suggestions
    - Timeline adjustments
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_progress(self, strategy_id: str) -> Dict:
        """
        Analyze current progress and identify issues

        Returns insights about:
        - Completion rate vs expected
        - Budget utilization
        - Bottlenecks
        - Risk areas
        """
        logger.info(f"📊 Analyzing progress for strategy {strategy_id}")

        strategy_data = await self._gather_strategy_data(strategy_id)

        prompt = self._build_analysis_prompt(strategy_data)

        result = await self._generate_with_llm(prompt)

        return {
            "suggestions": result.get("insights", []),
            "summary": result.get("summary", "Progress analysis completed."),
            "confidence_score": result.get("confidence", 0.7),
            "model": result.get("model", "template")
        }

    async def suggest_improvements(
        self,
        strategy_id: str,
        context: Optional[str] = None,
        specific_week: Optional[int] = None
    ) -> Dict:
        """
        Get improvement recommendations based on current state

        Args:
            strategy_id: Strategy UUID
            context: Additional context from user
            specific_week: Focus on specific week (1-13)

        Returns improvement suggestions for:
        - Task prioritization
        - Resource allocation
        - Tactical adjustments
        """
        logger.info(f"💡 Generating improvement suggestions for strategy {strategy_id}")

        strategy_data = await self._gather_strategy_data(strategy_id)

        prompt = self._build_improvement_prompt(strategy_data, context, specific_week)

        result = await self._generate_with_llm(prompt)

        return {
            "suggestions": result.get("improvements", []),
            "summary": result.get("summary", "Improvement suggestions generated."),
            "confidence_score": result.get("confidence", 0.75),
            "model": result.get("model", "template")
        }

    async def adjust_timeline(
        self,
        strategy_id: str,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Get timeline adjustment suggestions

        Args:
            strategy_id: Strategy UUID
            reason: Why timeline needs adjustment

        Returns:
        - Suggested task re-prioritization
        - Week focus adjustments
        - Deadline recommendations
        """
        logger.info(f"📅 Generating timeline adjustments for strategy {strategy_id}")

        strategy_data = await self._gather_strategy_data(strategy_id)

        prompt = self._build_timeline_prompt(strategy_data, reason)

        result = await self._generate_with_llm(prompt)

        return {
            "suggestions": result.get("adjustments", []),
            "summary": result.get("summary", "Timeline adjustment suggestions generated."),
            "confidence_score": result.get("confidence", 0.7),
            "model": result.get("model", "template")
        }

    async def _gather_strategy_data(self, strategy_id: str) -> Dict:
        """Gather all strategy data for analysis"""
        # Fetch strategy
        result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            return {}

        # Fetch weeks and tasks
        weeks_result = await self.db.execute(
            select(StrategyWeek)
            .where(StrategyWeek.strategy_id == strategy_id)
            .order_by(StrategyWeek.week_number)
        )
        weeks = weeks_result.scalars().all()

        weeks_data = []
        for week in weeks:
            tasks_result = await self.db.execute(
                select(StrategyTask)
                .where(StrategyTask.week_id == week.id)
            )
            tasks = tasks_result.scalars().all()

            weeks_data.append({
                "week_number": week.week_number,
                "focus_area": week.focus_area,
                "objectives": week.objectives,
                "completion_percentage": week.completion_percentage,
                "budget_allocated": week.budget_allocated,
                "tasks": [
                    {
                        "title": t.title,
                        "status": t.status.value,
                        "priority": t.priority.value,
                        "category": t.category,
                        "estimated_hours": t.estimated_hours,
                        "actual_hours": t.actual_hours
                    }
                    for t in tasks
                ]
            })

        # Calculate metrics
        now = datetime.utcnow()
        days_elapsed = max(0, (now - strategy.start_date).days)
        expected_progress = min(100, (days_elapsed / 90) * 100)

        return {
            "name": strategy.name,
            "primary_goal": strategy.primary_goal,
            "target_keywords": strategy.target_keywords,
            "total_budget": strategy.total_budget,
            "budget_spent": strategy.budget_spent,
            "completion_percentage": strategy.completion_percentage,
            "expected_progress": round(expected_progress, 1),
            "days_elapsed": days_elapsed,
            "days_remaining": 90 - days_elapsed,
            "kpi_targets": strategy.kpi_targets,
            "current_kpis": strategy.current_kpis,
            "weeks": weeks_data
        }

    def _build_analysis_prompt(self, data: Dict) -> str:
        """Build prompt for progress analysis"""
        return f"""Strateji ilerleme analizi yap.

**Strateji:** {data.get('name')}
**Hedef:** {data.get('primary_goal')}
**Tamamlanma:** {data.get('completion_percentage')}% (Beklenen: {data.get('expected_progress')}%)
**Bütçe:** ₺{data.get('budget_spent', 0):,.0f} / ₺{data.get('total_budget', 0):,.0f}
**Süre:** {data.get('days_elapsed')} gün geçti, {data.get('days_remaining')} gün kaldı

**Haftalık İlerleme:**
{json.dumps(data.get('weeks', []), indent=2, ensure_ascii=False)}

**İstenen Çıktı (JSON):**
{{
    "summary": "2-3 cümle özet",
    "insights": [
        {{"type": "risk|opportunity|warning|success", "title": "Başlık", "description": "Açıklama", "priority": "high|medium|low"}}
    ],
    "confidence": 0.8
}}

Türkçe yanıt ver. Sadece JSON formatında."""

    def _build_improvement_prompt(
        self,
        data: Dict,
        context: Optional[str],
        specific_week: Optional[int]
    ) -> str:
        """Build prompt for improvement suggestions"""
        week_focus = ""
        if specific_week:
            week_data = next(
                (w for w in data.get('weeks', []) if w['week_number'] == specific_week),
                None
            )
            if week_data:
                week_focus = f"\n**Odaklanılan Hafta {specific_week}:** {json.dumps(week_data, ensure_ascii=False)}"

        context_text = f"\n**Ek Bağlam:** {context}" if context else ""

        return f"""Strateji için iyileştirme önerileri sun.

**Strateji:** {data.get('name')}
**Hedef:** {data.get('primary_goal')}
**Tamamlanma:** {data.get('completion_percentage')}%
**Kalan Bütçe:** ₺{(data.get('total_budget', 0) or 0) - (data.get('budget_spent', 0) or 0):,.0f}
{context_text}
{week_focus}

**Haftalık Durum:**
{json.dumps(data.get('weeks', [])[:5], indent=2, ensure_ascii=False)}

**İstenen Çıktı (JSON):**
{{
    "summary": "Genel değerlendirme",
    "improvements": [
        {{"area": "content|seo|ads|budget|timeline", "title": "Öneri başlığı", "description": "Detaylı açıklama", "impact": "high|medium|low", "effort": "easy|medium|hard"}}
    ],
    "confidence": 0.75
}}

Türkçe yanıt ver. Pratik ve uygulanabilir öneriler sun. Sadece JSON formatında."""

    def _build_timeline_prompt(self, data: Dict, reason: Optional[str]) -> str:
        """Build prompt for timeline adjustments"""
        reason_text = f"\n**Neden:** {reason}" if reason else ""

        return f"""Strateji zaman çizelgesi ayarlama önerileri sun.

**Strateji:** {data.get('name')}
**Tamamlanma:** {data.get('completion_percentage')}%
**Kalan Süre:** {data.get('days_remaining')} gün
{reason_text}

**Mevcut Haftalık Plan:**
{json.dumps(data.get('weeks', []), indent=2, ensure_ascii=False)}

**İstenen Çıktı (JSON):**
{{
    "summary": "Zaman çizelgesi değerlendirmesi",
    "adjustments": [
        {{"type": "reprioritize|reschedule|add|remove", "week": 1, "description": "Yapılacak değişiklik", "reason": "Neden"}}
    ],
    "confidence": 0.7
}}

Türkçe yanıt ver. Sadece JSON formatında."""

    async def _generate_with_llm(self, prompt: str) -> Dict:
        """Generate response using LLM"""
        # Try Anthropic first
        if settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import Anthropic

                client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2048,
                    temperature=0.7,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                content = response.content[0].text
                result = json.loads(content)
                result["model"] = "claude-3-haiku"

                logger.info("✅ Refinement generated with Claude")
                return result

            except Exception as e:
                logger.error(f"❌ Claude refinement failed: {e}")

        # Try OpenAI
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.OPENAI_API_KEY)

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "system",
                        "content": "You are a strategic marketing consultant. Always respond in valid JSON format."
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    temperature=0.7,
                    max_tokens=2048,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content
                result = json.loads(content)
                result["model"] = "gpt-4o-mini"

                logger.info("✅ Refinement generated with OpenAI")
                return result

            except Exception as e:
                logger.error(f"❌ OpenAI refinement failed: {e}")

        # Fallback to template
        logger.warning("⚠️ Using template-based refinement")
        return self._template_response()

    def _template_response(self) -> Dict:
        """Fallback template response"""
        return {
            "summary": "AI API key not configured. Using template suggestions.",
            "insights": [
                {
                    "type": "warning",
                    "title": "AI Not Available",
                    "description": "Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for personalized insights.",
                    "priority": "medium"
                }
            ],
            "improvements": [
                {
                    "area": "content",
                    "title": "Review Content Strategy",
                    "description": "Analyze current content performance and optimize.",
                    "impact": "medium",
                    "effort": "medium"
                }
            ],
            "adjustments": [
                {
                    "type": "reprioritize",
                    "week": 1,
                    "description": "Review and adjust priorities based on current progress.",
                    "reason": "Standard review recommendation"
                }
            ],
            "confidence": 0.5,
            "model": "template"
        }
