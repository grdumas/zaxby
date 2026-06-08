"""
Tests for persona-based prompt templates (RPOPC-1016).
"""

import pytest
from src.persona_prompts import (
    get_persona_prompt,
    get_available_personas,
    format_comparison_context,
    PERSONA_PROMPTS,
)


def test_all_personas_defined():
    """Test that all expected persona types are defined."""
    assert "executive" in PERSONA_PROMPTS
    assert "tech_lead" in PERSONA_PROMPTS
    assert "expert" in PERSONA_PROMPTS


def test_persona_structure():
    """Test that each persona has required fields."""
    for persona_id, persona in PERSONA_PROMPTS.items():
        assert "name" in persona, f"{persona_id} missing 'name'"
        assert "description" in persona, f"{persona_id} missing 'description'"
        assert "system_prompt" in persona, f"{persona_id} missing 'system_prompt'"
        assert "user_prompt_template" in persona, f"{persona_id} missing 'user_prompt_template'"

        # Check that prompts are non-empty
        assert persona["name"], f"{persona_id} has empty name"
        assert persona["description"], f"{persona_id} has empty description"
        assert persona["system_prompt"], f"{persona_id} has empty system_prompt"
        assert persona["user_prompt_template"], f"{persona_id} has empty user_prompt_template"


def test_get_persona_prompt_executive():
    """Test getting executive persona prompts."""
    context = "Test context"
    system_prompt, user_prompt = get_persona_prompt("executive", context)

    assert "executive" in system_prompt.lower()
    assert "concise" in system_prompt.lower() or "pass/fail" in system_prompt.lower()
    assert context in user_prompt
    assert "executive" in user_prompt.lower() or "verdict" in user_prompt.lower()


def test_get_persona_prompt_tech_lead():
    """Test getting tech lead persona prompts."""
    context = "Test context"
    system_prompt, user_prompt = get_persona_prompt("tech_lead", context)

    assert "technical" in system_prompt.lower() or "tech" in system_prompt.lower()
    assert "trend" in system_prompt.lower() or "bottleneck" in system_prompt.lower()
    assert context in user_prompt


def test_get_persona_prompt_expert():
    """Test getting expert persona prompts."""
    context = "Test context"
    system_prompt, user_prompt = get_persona_prompt("expert", context)

    assert "expert" in system_prompt.lower() or "detailed" in system_prompt.lower()
    assert "metric" in system_prompt.lower() or "comprehensive" in system_prompt.lower()
    assert context in user_prompt


def test_get_persona_prompt_invalid():
    """Test that invalid persona raises ValueError."""
    with pytest.raises(ValueError, match="Invalid persona"):
        get_persona_prompt("invalid_persona", "context")


def test_get_available_personas():
    """Test getting list of available personas."""
    personas = get_available_personas()

    assert len(personas) == 3
    assert all("id" in p for p in personas)
    assert all("name" in p for p in personas)
    assert all("description" in p for p in personas)

    ids = [p["id"] for p in personas]
    assert "executive" in ids
    assert "tech_lead" in ids
    assert "expert" in ids


def test_format_comparison_context_basic():
    """Test basic comparison context formatting."""
    baseline = {"metric1": 100, "metric2": 200}
    comparison = {"metric1": 110, "metric2": 180}

    context = format_comparison_context(baseline, comparison)

    assert "Baseline Performance" in context
    assert "Comparison Performance" in context
    assert "Performance Delta" in context
    assert "metric1" in context
    assert "metric2" in context


def test_format_comparison_context_with_metadata():
    """Test comparison context formatting with metadata."""
    baseline = {"throughput": 1000}
    comparison = {"throughput": 1200}
    metadata = {
        "OS Version": "RHEL 9.5 → RHEL 9.6",
        "Hardware": "AWS m5.xlarge"
    }

    context = format_comparison_context(baseline, comparison, metadata)

    assert "Comparison Scope" in context
    assert "RHEL 9.5" in context
    assert "AWS m5.xlarge" in context
    assert "throughput" in context


def test_format_comparison_context_percentage_calculation():
    """Test that percentage changes are calculated correctly."""
    baseline = {"score": 100}
    comparison = {"score": 150}

    context = format_comparison_context(baseline, comparison)

    # Should show +50 and +50.0%
    assert "+50" in context
    assert "%" in context


def test_format_comparison_context_regression():
    """Test formatting shows negative changes (regression)."""
    baseline = {"latency": 100}
    comparison = {"latency": 120}

    context = format_comparison_context(baseline, comparison)

    # Should show +20 (increase in latency is bad)
    assert "+20" in context or "+20.0" in context


def test_format_comparison_context_non_numeric():
    """Test formatting handles non-numeric values gracefully."""
    baseline = {"status": "pass", "score": 100}
    comparison = {"status": "fail", "score": 80}

    context = format_comparison_context(baseline, comparison)

    assert "pass → fail" in context
    assert "-20" in context  # Numeric still calculated


def test_format_comparison_context_zero_baseline():
    """Test handling of zero baseline values."""
    baseline = {"new_metric": 0}
    comparison = {"new_metric": 100}

    context = format_comparison_context(baseline, comparison)

    # Should handle division by zero gracefully
    assert "100" in context or "+100" in context


def test_persona_prompts_have_format_placeholders():
    """Test that user prompt templates have the required placeholder."""
    for persona_id, persona in PERSONA_PROMPTS.items():
        template = persona["user_prompt_template"]
        assert "{comparison_context}" in template, (
            f"{persona_id} user_prompt_template missing {{comparison_context}} placeholder"
        )


def test_executive_persona_emphasizes_clarity():
    """Test that executive persona emphasizes clear, concise communication."""
    system_prompt = PERSONA_PROMPTS["executive"]["system_prompt"]

    # Check for executive-appropriate keywords
    executive_keywords = ["concise", "verdict", "impact", "action", "executive"]
    assert any(keyword in system_prompt.lower() for keyword in executive_keywords)


def test_tech_lead_persona_emphasizes_actionability():
    """Test that tech lead persona emphasizes actionable technical insights."""
    system_prompt = PERSONA_PROMPTS["tech_lead"]["system_prompt"]

    # Check for tech lead-appropriate keywords
    tech_lead_keywords = ["trend", "bottleneck", "recommendation", "technical", "optimize"]
    assert any(keyword in system_prompt.lower() for keyword in tech_lead_keywords)


def test_expert_persona_emphasizes_detail():
    """Test that expert persona emphasizes comprehensive technical detail."""
    system_prompt = PERSONA_PROMPTS["expert"]["system_prompt"]

    # Check for expert-appropriate keywords
    expert_keywords = ["detailed", "comprehensive", "metric", "variance", "analysis", "deep"]
    assert any(keyword in system_prompt.lower() for keyword in expert_keywords)
