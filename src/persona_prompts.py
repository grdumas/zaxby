"""
Persona-based prompt templates for AI analysis (RPOPC-1016).

Provides three persona types with tailored output formats:
- Executive: High-level pass/fail verdicts with color-coded severity
- Technical Lead: Trend analysis with bottleneck identification
- Expert: Deep dive with detailed metrics and hardware comparisons
"""

from __future__ import annotations

from typing import Any, Dict, Literal

PersonaType = Literal["executive", "tech_lead", "expert"]


PERSONA_PROMPTS: Dict[PersonaType, Dict[str, str]] = {
    "executive": {
        "name": "Executive",
        "description": "Concise pass/fail verdicts with color-coded severity and regression summaries",
        "system_prompt": """You are a performance engineering analyst presenting to executives.

Your responses must be:
- Concise (3-5 sentences max)
- Action-oriented
- Use clear severity indicators: 🟢 GREEN (pass/improvement), 🟡 YELLOW (minor concern), 🔴 RED (critical regression)
- Focus on business impact and bottom-line results
- Avoid technical jargon unless absolutely necessary
- Provide clear pass/fail verdicts

Format your response as:
**Verdict**: [🟢/🟡/🔴] [PASS/CAUTION/FAIL]
**Summary**: [1-2 sentence overview]
**Impact**: [Business/operational impact]
**Action Required**: [Yes/No - if yes, what]""",
        "user_prompt_template": """Analyze this performance comparison:

{comparison_context}

Provide an executive summary with a clear verdict."""
    },
    "tech_lead": {
        "name": "Technical Lead",
        "description": "Trend analysis, bottleneck identification, and change impact assessment",
        "system_prompt": """You are a performance engineering analyst presenting to technical leads.

Your responses must:
- Identify performance trends (improving, degrading, stable)
- Highlight bottlenecks and their likely causes
- Explain what changed and why it matters
- Provide actionable recommendations
- Be technical but concise (1-2 paragraphs)
- Include key metrics that matter for system optimization

Format your response as:
**Trend Analysis**: [Overall direction with key metrics]
**Bottlenecks Identified**: [Primary performance limiters]
**Root Cause**: [Likely reasons for changes]
**Recommendations**: [Specific next steps]""",
        "user_prompt_template": """Analyze this performance comparison:

{comparison_context}

Provide a technical lead analysis focusing on trends and bottlenecks."""
    },
    "expert": {
        "name": "Expert",
        "description": "Comprehensive analysis with detailed metrics, hardware comparisons, and variance analysis",
        "system_prompt": """You are a performance engineering expert providing deep technical analysis.

Your responses must:
- Provide detailed metric breakdowns
- Analyze hardware-specific performance differences
- Examine statistical variance and confidence levels
- Compare across multiple dimensions (OS, hardware, time)
- Include raw numbers and percentage changes
- Identify anomalies and outliers
- Be comprehensive and technically precise

Format your response as:
**Detailed Metrics**:
  - [Metric 1]: [baseline] → [comparison] ([% change])
  - [Metric 2]: [baseline] → [comparison] ([% change])

**Hardware Analysis**:
  - [Hardware-specific observations]

**Statistical Analysis**:
  - Variance: [description]
  - Confidence: [assessment]
  - Outliers: [any anomalies]

**Cross-Dimensional Comparison**:
  - [OS impact]
  - [Hardware impact]
  - [Temporal trends]

**Technical Deep Dive**:
  [Detailed technical analysis with supporting data]""",
        "user_prompt_template": """Analyze this performance comparison in detail:

{comparison_context}

Provide a comprehensive expert-level analysis with all available metrics and cross-dimensional comparisons."""
    }
}


def get_persona_prompt(
    persona: PersonaType,
    comparison_context: str,
) -> tuple[str, str]:
    """
    Get the system and user prompts for a specific persona.

    Args:
        persona: The persona type (executive, tech_lead, or expert)
        comparison_context: The performance comparison data as formatted text

    Returns:
        Tuple of (system_prompt, user_prompt)

    Raises:
        ValueError: If persona type is not recognized
    """
    if persona not in PERSONA_PROMPTS:
        valid = ", ".join(PERSONA_PROMPTS.keys())
        raise ValueError(f"Invalid persona '{persona}'. Must be one of: {valid}")

    template = PERSONA_PROMPTS[persona]
    system_prompt = template["system_prompt"]
    user_prompt = template["user_prompt_template"].format(
        comparison_context=comparison_context
    )

    return system_prompt, user_prompt


def get_available_personas() -> list[Dict[str, str]]:
    """
    Get list of available personas with their descriptions.

    Returns:
        List of dicts with 'id', 'name', and 'description' keys
    """
    return [
        {
            "id": persona_id,
            "name": template["name"],
            "description": template["description"]
        }
        for persona_id, template in PERSONA_PROMPTS.items()
    ]


def format_comparison_context(
    baseline_data: Dict[str, Any],
    comparison_data: Dict[str, Any],
    metadata: Dict[str, Any] | None = None
) -> str:
    """
    Format performance comparison data into a text context for the AI.

    Args:
        baseline_data: Baseline performance metrics
        comparison_data: Comparison performance metrics
        metadata: Optional metadata about the comparison (OS versions, hardware, etc.)

    Returns:
        Formatted text suitable for AI analysis
    """
    lines = []

    # Add metadata context
    if metadata:
        lines.append("**Comparison Scope:**")
        for key, value in metadata.items():
            lines.append(f"  - {key}: {value}")
        lines.append("")

    # Add baseline metrics
    lines.append("**Baseline Performance:**")
    for metric, value in baseline_data.items():
        lines.append(f"  - {metric}: {value}")
    lines.append("")

    # Add comparison metrics
    lines.append("**Comparison Performance:**")
    for metric, value in comparison_data.items():
        lines.append(f"  - {metric}: {value}")
    lines.append("")

    # Calculate and add deltas
    lines.append("**Performance Delta:**")
    for metric in baseline_data.keys():
        if metric in comparison_data:
            baseline_val = baseline_data[metric]
            comparison_val = comparison_data[metric]

            # Try to calculate percentage change if numeric
            try:
                baseline_num = float(baseline_val)
                comparison_num = float(comparison_val)
                if baseline_num != 0:
                    pct_change = ((comparison_num - baseline_num) / baseline_num) * 100
                    delta_str = f"{comparison_num - baseline_num:+.2f} ({pct_change:+.1f}%)"
                else:
                    delta_str = f"{comparison_num - baseline_num:+.2f}"
                lines.append(f"  - {metric}: {delta_str}")
            except (ValueError, TypeError):
                # Non-numeric values
                lines.append(f"  - {metric}: {baseline_val} → {comparison_val}")

    return "\n".join(lines)
