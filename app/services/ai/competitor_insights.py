"""
AI-Powered Competitor Insights Service

Generates SWOT analysis, recommendations, and competitive intelligence using LLMs.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class CompetitorInsightsService:
    """
    AI service for generating competitor insights using Claude or GPT-4
    """

    SYSTEM_PROMPT = """You are a competitive intelligence analyst specializing in digital marketing and SEO.
Your task is to analyze competitor data and provide actionable insights.

When analyzing competitors, consider:
1. Domain authority and backlink profile strength
2. Organic traffic and keyword rankings
3. Content strategy and coverage
4. Technical SEO factors
5. Paid advertising presence
6. Market positioning

Provide insights in a structured format with clear, actionable recommendations.
Be specific and data-driven in your analysis.
"""

    def __init__(self):
        self.has_anthropic = bool(settings.ANTHROPIC_API_KEY)
        self.has_openai = bool(settings.OPENAI_API_KEY)

    async def generate_swot_analysis(
        self,
        competitor_data: Dict[str, Any],
        user_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate SWOT analysis for a competitor

        Args:
            competitor_data: Competitor metrics and information
            user_domain: Optional user's domain for comparison

        Returns:
            SWOT analysis with strengths, weaknesses, opportunities, threats
        """
        prompt = self._build_swot_prompt(competitor_data, user_domain)

        if self.has_anthropic:
            response = await self._call_claude(prompt)
        elif self.has_openai:
            response = await self._call_openai(prompt)
        else:
            return self._generate_fallback_swot(competitor_data)

        return self._parse_swot_response(response, competitor_data)

    async def generate_recommendations(
        self,
        competitor_data: Dict[str, Any],
        user_metrics: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate actionable recommendations based on competitor analysis

        Args:
            competitor_data: Competitor metrics
            user_metrics: Optional user's current metrics for comparison

        Returns:
            List of actionable recommendations
        """
        prompt = self._build_recommendations_prompt(competitor_data, user_metrics)

        if self.has_anthropic:
            response = await self._call_claude(prompt)
        elif self.has_openai:
            response = await self._call_openai(prompt)
        else:
            return self._generate_fallback_recommendations(competitor_data)

        return self._parse_recommendations(response)

    async def identify_content_gaps(
        self,
        competitor_keywords: List[Dict],
        user_keywords: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Identify content gap opportunities using AI analysis

        Args:
            competitor_keywords: Keywords the competitor ranks for
            user_keywords: Keywords the user ranks for

        Returns:
            List of content gap opportunities with recommendations
        """
        # Find keywords competitor has but user doesn't
        user_kw_set = {k.get("keyword", "").lower() for k in user_keywords}
        gaps = [k for k in competitor_keywords if k.get("keyword", "").lower() not in user_kw_set]

        # Sort by search volume
        gaps = sorted(gaps, key=lambda x: x.get("search_volume", 0), reverse=True)[:50]

        if not gaps:
            return []

        # Use AI to categorize and prioritize
        prompt = self._build_content_gap_prompt(gaps)

        if self.has_anthropic:
            response = await self._call_claude(prompt)
            return self._parse_content_gaps(response, gaps)
        elif self.has_openai:
            response = await self._call_openai(prompt)
            return self._parse_content_gaps(response, gaps)
        else:
            return self._generate_fallback_content_gaps(gaps)

    def _build_swot_prompt(self, competitor_data: Dict, user_domain: Optional[str]) -> str:
        """Build prompt for SWOT analysis"""
        domain = competitor_data.get("domain", "Unknown")
        da = competitor_data.get("domain_authority", 0)
        traffic = competitor_data.get("organic_traffic", 0)
        keywords = competitor_data.get("organic_keywords", 0)
        backlinks = competitor_data.get("total_backlinks", 0)
        referring_domains = competitor_data.get("referring_domains", 0)

        prompt = f"""Analyze the following competitor and provide a SWOT analysis:

COMPETITOR: {domain}

METRICS:
- Domain Authority: {da}/100
- Monthly Organic Traffic: {traffic:,}
- Ranking Keywords: {keywords:,}
- Total Backlinks: {backlinks:,}
- Referring Domains: {referring_domains:,}
"""

        if user_domain:
            prompt += f"\nComparing against: {user_domain}\n"

        prompt += """
Please provide a detailed SWOT analysis in the following JSON format:
{
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "opportunities": ["opportunity1", "opportunity2", ...],
    "threats": ["threat1", "threat2", ...]
}

Be specific and actionable. Focus on SEO, content, and digital marketing aspects.
Return ONLY the JSON, no additional text.
"""
        return prompt

    def _build_recommendations_prompt(
        self,
        competitor_data: Dict,
        user_metrics: Optional[Dict]
    ) -> str:
        """Build prompt for recommendations"""
        domain = competitor_data.get("domain", "Unknown")
        da = competitor_data.get("domain_authority", 0)
        traffic = competitor_data.get("organic_traffic", 0)

        prompt = f"""Based on the competitor analysis for {domain}:

COMPETITOR METRICS:
- Domain Authority: {da}/100
- Monthly Organic Traffic: {traffic:,}
- Ranking Keywords: {competitor_data.get("organic_keywords", 0):,}
- Backlinks: {competitor_data.get("total_backlinks", 0):,}
"""

        if user_metrics:
            prompt += f"""
YOUR METRICS:
- Domain Authority: {user_metrics.get("domain_authority", 0)}/100
- Monthly Organic Traffic: {user_metrics.get("organic_traffic", 0):,}
"""

        prompt += """
Provide 5-7 specific, actionable recommendations to outrank this competitor.
Return as a JSON array of strings:
["recommendation1", "recommendation2", ...]

Focus on:
1. Quick wins (low effort, high impact)
2. Long-term strategies
3. Content opportunities
4. Technical improvements
5. Link building tactics

Return ONLY the JSON array, no additional text.
"""
        return prompt

    def _build_content_gap_prompt(self, gaps: List[Dict]) -> str:
        """Build prompt for content gap analysis"""
        keywords_text = "\n".join([
            f"- {g.get('keyword', '')} (Volume: {g.get('search_volume', 0):,})"
            for g in gaps[:30]
        ])

        return f"""Analyze these keyword gaps (keywords your competitor ranks for but you don't):

{keywords_text}

Categorize these keywords and identify content opportunities.
Return as JSON:
{{
    "categories": [
        {{
            "name": "Category Name",
            "keywords": ["keyword1", "keyword2"],
            "content_type": "blog|landing|product|guide",
            "priority": "high|medium|low",
            "recommendation": "Specific content recommendation"
        }}
    ]
}}

Return ONLY the JSON, no additional text.
"""

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API"""
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.3,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return ""

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ""

    def _parse_swot_response(self, response: str, competitor_data: Dict) -> Dict[str, Any]:
        """Parse SWOT response from AI"""
        import json
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            return {
                "domain": competitor_data.get("domain", ""),
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "opportunities": data.get("opportunities", []),
                "threats": data.get("threats", []),
                "recommendations": [],
                "generated_at": datetime.utcnow()
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse SWOT JSON, using fallback")
            return self._generate_fallback_swot(competitor_data)

    def _parse_recommendations(self, response: str) -> List[str]:
        """Parse recommendations from AI response"""
        import json
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            return json.loads(response.strip())
        except json.JSONDecodeError:
            logger.warning("Failed to parse recommendations JSON")
            return []

    def _parse_content_gaps(self, response: str, gaps: List[Dict]) -> List[Dict[str, Any]]:
        """Parse content gap analysis from AI"""
        import json
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            return data.get("categories", [])
        except json.JSONDecodeError:
            return self._generate_fallback_content_gaps(gaps)

    def _generate_fallback_swot(self, competitor_data: Dict) -> Dict[str, Any]:
        """Generate fallback SWOT when AI is unavailable"""
        da = competitor_data.get("domain_authority", 0)
        traffic = competitor_data.get("organic_traffic", 0)
        keywords = competitor_data.get("organic_keywords", 0)
        backlinks = competitor_data.get("total_backlinks", 0)

        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        # Analyze based on metrics
        if da >= 50:
            strengths.append("Strong domain authority indicates established online presence")
            threats.append("High DA makes them a formidable competitor in search rankings")
        else:
            weaknesses.append("Lower domain authority suggests room for growth")
            opportunities.append("Opportunity to outrank through quality content and link building")

        if traffic >= 50000:
            strengths.append("High organic traffic indicates strong content and SEO strategy")
        else:
            weaknesses.append("Moderate organic traffic suggests content gaps")
            opportunities.append("Content creation opportunity in underserved topics")

        if keywords >= 1000:
            strengths.append("Broad keyword coverage across many topics")
        else:
            opportunities.append("Niche keyword opportunities they may not be targeting")

        if backlinks >= 5000:
            strengths.append("Strong backlink profile provides ranking authority")
        else:
            opportunities.append("Link building gap - opportunity to build superior profile")

        return {
            "domain": competitor_data.get("domain", ""),
            "strengths": strengths or ["Established online presence"],
            "weaknesses": weaknesses or ["Limited data available for analysis"],
            "opportunities": opportunities or ["Market entry opportunities exist"],
            "threats": threats or ["Competitive landscape requires monitoring"],
            "recommendations": [
                "Focus on content quality and comprehensive coverage",
                "Build authoritative backlinks from industry sources",
                "Target long-tail keywords for quick wins",
                "Monitor competitor content updates regularly"
            ],
            "generated_at": datetime.utcnow()
        }

    def _generate_fallback_recommendations(self, competitor_data: Dict) -> List[str]:
        """Generate fallback recommendations when AI is unavailable"""
        da = competitor_data.get("domain_authority", 0)

        recommendations = [
            "Analyze competitor's top-performing content and create superior versions",
            "Identify and target keyword gaps where they rank but you don't",
            "Build relationships for guest posting on sites linking to them",
            "Improve page speed and Core Web Vitals for better rankings"
        ]

        if da < 40:
            recommendations.append("Focus on building domain authority through quality backlinks")
        else:
            recommendations.append("Target their weakest ranking keywords for quick wins")

        return recommendations

    def _generate_fallback_content_gaps(self, gaps: List[Dict]) -> List[Dict[str, Any]]:
        """Generate fallback content gap analysis"""
        if not gaps:
            return []

        # Group by rough categories based on keywords
        categories = {}
        for gap in gaps[:20]:
            keyword = gap.get("keyword", "")
            volume = gap.get("search_volume", 0)

            # Simple categorization
            if any(word in keyword.lower() for word in ["how", "guide", "tutorial"]):
                cat = "Educational Content"
            elif any(word in keyword.lower() for word in ["best", "top", "review"]):
                cat = "Comparison/Review Content"
            elif any(word in keyword.lower() for word in ["buy", "price", "cost"]):
                cat = "Commercial Content"
            else:
                cat = "General Topics"

            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "keywords": [],
                    "total_volume": 0,
                    "content_type": "blog",
                    "priority": "medium"
                }
            categories[cat]["keywords"].append(keyword)
            categories[cat]["total_volume"] += volume

        # Convert to list and sort by volume
        result = list(categories.values())
        result.sort(key=lambda x: x["total_volume"], reverse=True)

        # Set priorities
        for i, cat in enumerate(result):
            cat["priority"] = "high" if i == 0 else "medium" if i < 3 else "low"
            cat["recommendation"] = f"Create comprehensive content targeting these {len(cat['keywords'])} keywords"
            del cat["total_volume"]

        return result
