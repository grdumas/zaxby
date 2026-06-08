"""
Summary text generation for dashboard insights.

Provides human-readable summaries of analysis results.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import logging

from src.regression_detection import (
    REGRESSION_THRESHOLD_REL,
    is_improvement_for_test_name,
    is_regression_for_test_name,
    percent_change,
)

logger = logging.getLogger(__name__)


def format_regression_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format regression analysis into a readable summary.
    
    Args:
        analysis_result: Result from analyze_os_version_regressions
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No regression analysis available"
    
    return analysis_result['summary']


def format_peer_comparison_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format peer OS comparison into a readable summary.
    
    Args:
        analysis_result: Result from analyze_peer_os_comparison
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No peer comparison data available"
    
    return analysis_result['summary']


def format_scaling_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format cloud scaling analysis into a readable summary.
    
    Args:
        analysis_result: Result from analyze_cloud_scaling
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No scaling analysis available"
    
    return analysis_result['summary']


def get_status_icon(num_issues: int) -> str:
    """
    Get an appropriate status icon based on number of issues.
    
    Args:
        num_issues: Number of issues detected
        
    Returns:
        Status icon (emoji or symbol)
    """
    if num_issues == 0:
        return "✅"
    elif num_issues <= 2:
        return "⚠️"
    else:
        return "🔴"


def create_alert_badge(text: str, severity: str = "warning") -> str:
    """
    Create an alert badge for display.
    
    Args:
        text: Alert text
        severity: One of "success", "warning", "danger", "info"
        
    Returns:
        Formatted badge HTML class
    """
    severity_map = {
        "success": "success",
        "warning": "warning",
        "danger": "danger",
        "info": "info"
    }
    
    return severity_map.get(severity, "info")


def summarize_investigation_details(
    baseline_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    test_name: str,
    baseline_label: str,
    comparison_label: str
) -> Dict[str, Any]:
    """
    Create a detailed summary for investigation view.
    
    Args:
        baseline_df: Baseline data
        comparison_df: Comparison data
        test_name: Test name
        baseline_label: Label for baseline
        comparison_label: Label for comparison
        
    Returns:
        Dictionary with summary details
    """
    summary = {
        'test_name': test_name,
        'baseline_label': baseline_label,
        'comparison_label': comparison_label,
        'baseline_count': len(baseline_df),
        'comparison_count': len(comparison_df)
    }
    
    if not baseline_df.empty and 'primary_metric_value' in baseline_df.columns:
        summary['baseline_mean'] = baseline_df['primary_metric_value'].mean()
        summary['baseline_std'] = baseline_df['primary_metric_value'].std()
        summary['baseline_min'] = baseline_df['primary_metric_value'].min()
        summary['baseline_max'] = baseline_df['primary_metric_value'].max()
    
    if not comparison_df.empty and 'primary_metric_value' in comparison_df.columns:
        summary['comparison_mean'] = comparison_df['primary_metric_value'].mean()
        summary['comparison_std'] = comparison_df['primary_metric_value'].std()
        summary['comparison_min'] = comparison_df['primary_metric_value'].min()
        summary['comparison_max'] = comparison_df['primary_metric_value'].max()
    
    # Calculate regression metrics
    if 'baseline_mean' in summary and 'comparison_mean' in summary and summary['baseline_mean'] > 0:
        summary['percent_change'] = percent_change(
            summary['baseline_mean'], summary['comparison_mean']
        )
        summary['is_regression'] = is_regression_for_test_name(
            summary['percent_change'],
            test_name,
            regression_threshold=REGRESSION_THRESHOLD_REL,
        )
        summary['is_improvement'] = is_improvement_for_test_name(
            summary['percent_change'],
            test_name,
        )
        
        if summary['is_regression']:
            summary['status'] = 'danger'
            summary['status_text'] = 'Regression Detected'
        elif summary['is_improvement']:
            summary['status'] = 'success'
            summary['status_text'] = 'Performance Improvement'
        else:
            summary['status'] = 'info'
            summary['status_text'] = 'Stable Performance'
    
    return summary


def format_investigation_summary_text(summary: Dict[str, Any]) -> str:
    """
    Format investigation summary as readable text.

    Args:
        summary: Summary dictionary from summarize_investigation_details

    Returns:
        Formatted text summary
    """
    lines = []

    if 'baseline_mean' in summary and 'comparison_mean' in summary:
        lines.append(f"**{summary['baseline_label']}**: {summary['baseline_mean']:,.1f} (avg)")
        lines.append(f"**{summary['comparison_label']}**: {summary['comparison_mean']:,.1f} (avg)")

        if 'percent_change' in summary:
            direction = "↑" if summary['percent_change'] > 0 else "↓"
            lines.append(f"**Change**: {direction} {abs(summary['percent_change']):.1f}%")

    if 'baseline_count' in summary:
        lines.append(f"**Sample sizes**: {summary['baseline_count']} vs {summary['comparison_count']} tests")

    return "\n\n".join(lines)


def generate_ai_analysis(
    summary: Dict[str, Any],
    persona: str = "tech_lead"
) -> Optional[str]:
    """
    Generate AI-powered analysis of investigation summary (RPOPC-1016).

    Args:
        summary: Summary dictionary from summarize_investigation_details
        persona: Analysis persona (executive, tech_lead, or expert)

    Returns:
        AI-generated analysis text, or None if AI service is unavailable
    """
    try:
        from src.ai_analysis import analyze_performance_comparison

        # Extract baseline and comparison data from summary
        baseline_data = {}
        comparison_data = {}

        if 'baseline_mean' in summary:
            baseline_data['average'] = summary['baseline_mean']
        if 'baseline_std' in summary:
            baseline_data['std_dev'] = summary['baseline_std']
        if 'baseline_min' in summary and 'baseline_max' in summary:
            baseline_data['range'] = f"{summary['baseline_min']:.1f} - {summary['baseline_max']:.1f}"
        if 'baseline_count' in summary:
            baseline_data['sample_size'] = summary['baseline_count']

        if 'comparison_mean' in summary:
            comparison_data['average'] = summary['comparison_mean']
        if 'comparison_std' in summary:
            comparison_data['std_dev'] = summary['comparison_std']
        if 'comparison_min' in summary and 'comparison_max' in summary:
            comparison_data['range'] = f"{summary['comparison_min']:.1f} - {summary['comparison_max']:.1f}"
        if 'comparison_count' in summary:
            comparison_data['sample_size'] = summary['comparison_count']

        # Build metadata
        metadata = {
            'test': summary.get('test_name', 'Unknown Test'),
            'baseline': summary.get('baseline_label', 'Baseline'),
            'comparison': summary.get('comparison_label', 'Comparison'),
        }

        if 'percent_change' in summary:
            metadata['percent_change'] = f"{summary['percent_change']:+.1f}%"
        if 'status_text' in summary:
            metadata['assessment'] = summary['status_text']

        # Generate analysis
        analysis = analyze_performance_comparison(
            baseline_data=baseline_data,
            comparison_data=comparison_data,
            metadata=metadata,
            persona=persona
        )

        return analysis

    except ImportError:
        logger.debug("AI analysis not available (anthropic package not installed)")
        return None
    except Exception as e:
        logger.warning(f"AI analysis failed: {e}")
        return None

