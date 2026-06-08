"""
AI-powered performance analysis service (RPOPC-1016).

Integrates with Claude API to provide persona-based analysis of performance data.
Requires ANTHROPIC_API_KEY environment variable to be set.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from src.persona_prompts import (
    PersonaType,
    get_persona_prompt,
    format_comparison_context,
)

logger = logging.getLogger(__name__)


class AIAnalysisError(Exception):
    """Raised when AI analysis fails."""
    pass


class AIAnalysisService:
    """
    Service for AI-powered performance analysis using Claude API.

    Supports three persona types: executive, tech_lead, and expert.
    Each persona provides a different level of detail and focus.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI analysis service.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.

        Raises:
            AIAnalysisError: If API key is not available
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise AIAnalysisError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "AI analysis features are disabled."
            )

        # Lazy import to avoid requiring anthropic package if not using AI features
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self._anthropic = anthropic
        except ImportError:
            raise AIAnalysisError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

    def analyze_comparison(
        self,
        baseline_data: Dict[str, Any],
        comparison_data: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
        persona: PersonaType = "tech_lead",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2048,
    ) -> str:
        """
        Analyze performance comparison data using AI with specified persona.

        Args:
            baseline_data: Baseline performance metrics
            comparison_data: Comparison performance metrics
            metadata: Optional metadata about the comparison
            persona: Analysis persona (executive, tech_lead, or expert)
            model: Claude model to use
            max_tokens: Maximum tokens in response

        Returns:
            AI-generated analysis text formatted for the persona

        Raises:
            AIAnalysisError: If analysis fails
        """
        try:
            # Format the comparison context
            context = format_comparison_context(
                baseline_data,
                comparison_data,
                metadata
            )

            # Get persona-specific prompts
            system_prompt, user_prompt = get_persona_prompt(persona, context)

            # Call Claude API
            logger.info(f"Requesting AI analysis with persona={persona}, model={model}")
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract text from response
            if not message.content:
                raise AIAnalysisError("Empty response from AI")

            # Handle different response types
            response_text = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            if not response_text:
                raise AIAnalysisError("No text content in AI response")

            logger.info(f"AI analysis completed successfully ({len(response_text)} chars)")
            return response_text

        except self._anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise AIAnalysisError(f"AI service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in AI analysis: {e}")
            raise AIAnalysisError(f"Analysis failed: {str(e)}")

    def is_available(self) -> bool:
        """
        Check if AI analysis is available (API key configured).

        Returns:
            True if AI analysis can be performed
        """
        return bool(self.api_key)


# Global service instance (lazy initialization)
_service: Optional[AIAnalysisService] = None


def get_ai_analysis_service() -> Optional[AIAnalysisService]:
    """
    Get the global AI analysis service instance.

    Returns:
        AIAnalysisService instance if API key is configured, None otherwise
    """
    global _service

    if _service is None:
        try:
            _service = AIAnalysisService()
        except AIAnalysisError as e:
            logger.warning(f"AI analysis service unavailable: {e}")
            return None

    return _service


def analyze_performance_comparison(
    baseline_data: Dict[str, Any],
    comparison_data: Dict[str, Any],
    metadata: Dict[str, Any] | None = None,
    persona: PersonaType = "tech_lead",
) -> Optional[str]:
    """
    Convenience function to analyze performance comparison.

    Args:
        baseline_data: Baseline performance metrics
        comparison_data: Comparison performance metrics
        metadata: Optional metadata about the comparison
        persona: Analysis persona (executive, tech_lead, or expert)

    Returns:
        AI-generated analysis text, or None if AI service is unavailable
    """
    service = get_ai_analysis_service()
    if service is None:
        return None

    try:
        return service.analyze_comparison(
            baseline_data,
            comparison_data,
            metadata,
            persona
        )
    except AIAnalysisError as e:
        logger.error(f"Failed to analyze comparison: {e}")
        return None
