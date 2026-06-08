  # AI-Powered Performance Analysis (RPOPC-1016)

## Overview

The Performance Engineering Dashboard includes AI-powered analysis capabilities that provide intelligent insights into performance comparisons. The system uses Claude (Anthropic's AI) to analyze benchmark data and generate persona-specific reports tailored to different audiences.

## Features

### Three Persona Types

The AI analysis system provides three distinct analysis personas, each optimized for a specific audience:

#### 1. Executive Persona
**Target Audience:** Executives, managers, decision-makers  
**Output Style:** Concise, high-level verdicts

**Characteristics:**
- **Pass/fail verdicts** with color-coded severity indicators (🟢 🟡 🔴)
- **3-5 sentence summaries** focusing on business impact
- **Action-oriented recommendations**
- **Minimal technical jargon**
- Clear bottom-line results

**Example Output:**
```
**Verdict**: 🔴 FAIL
**Summary**: Performance degraded by 23% in the RHEL 9.6 upgrade on AWS m5.xlarge instances.
**Impact**: Critical regression affecting production workload capacity.
**Action Required**: Yes - investigate before production rollout.
```

#### 2. Technical Lead Persona
**Target Audience:** Engineering leads, architects, team leads  
**Output Style:** Balanced technical depth with actionable insights

**Characteristics:**
- **Trend analysis** (improving, degrading, stable)
- **Bottleneck identification** with likely root causes
- **Technical recommendations** for optimization
- **Key metric highlights** relevant to system performance
- 1-2 paragraph depth

**Example Output:**
```
**Trend Analysis**: Throughput declined 15% while latency increased 8%, indicating resource contention.
**Bottlenecks Identified**: CPU utilization spiked to 85%, suggesting compute-bound workload.
**Root Cause**: Likely related to kernel scheduler changes in RHEL 9.6.
**Recommendations**: Profile CPU hotspots; consider instance upgrade or workload tuning.
```

#### 3. Expert Persona
**Target Audience:** Performance engineers, specialists, deep-dive analysts  
**Output Style:** Comprehensive technical analysis

**Characteristics:**
- **Detailed metric breakdowns** with raw numbers and percentages
- **Hardware-specific performance analysis**
- **Statistical variance and confidence assessments**
- **Cross-dimensional comparisons** (OS, hardware, temporal)
- **Anomaly and outlier identification**
- Comprehensive technical depth

**Example Output:**
```
**Detailed Metrics**:
  - Throughput: 1000 ops/s → 850 ops/s (-15.0%)
  - Latency p50: 50ms → 54ms (+8.0%)
  - Latency p99: 120ms → 145ms (+20.8%)
  - CPU Usage: 60% → 85% (+41.7%)

**Hardware Analysis**:
  - AWS m5.xlarge (4 vCPUs, 16GB RAM) shows consistent degradation
  - Pattern suggests CPU-bound workload hitting capacity limits

**Statistical Analysis**:
  - Variance: High consistency (σ = 2.3% baseline, 3.1% comparison)
  - Confidence: 95% CI shows statistically significant regression
  - Outliers: None detected (z-score < 2.5 for all samples)

**Cross-Dimensional Comparison**:
  - OS impact: RHEL 9.5 → 9.6 shows regression across all workloads
  - Hardware impact: Consistent across m5 instance family
  - Temporal trends: Degradation appeared in last 2 weeks

**Technical Deep Dive**:
Kernel 5.14.x (RHEL 9.6) introduces new scheduler changes that may affect
CPU-intensive workloads. The p99 latency spike (+20.8%) suggests increased
tail latency variance. Recommend profiling with perf to identify specific
hotspots and comparing kernel parameters between versions.
```

## Configuration

### Prerequisites

1. **Anthropic API Key**: Obtain from [Anthropic Console](https://console.anthropic.com/)
2. **Python Package**: `anthropic>=0.39.0` (included in requirements.txt)

### Environment Setup

Add your Anthropic API key to `.env`:

```bash
# AI Analysis Configuration (RPOPC-1016)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Note:** The API key is optional. If not configured, the AI analysis features will be gracefully disabled without affecting other dashboard functionality.

### Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (includes anthropic package)
pip install -r requirements.txt
```

## Usage

### Programmatic API

#### Basic Analysis

```python
from src.ai_analysis import analyze_performance_comparison

# Define baseline and comparison data
baseline_data = {
    "throughput": 1000,
    "latency": 50,
    "cpu_usage": 60
}

comparison_data = {
    "throughput": 850,
    "latency": 54,
    "cpu_usage": 85
}

metadata = {
    "test": "benchmark_xyz",
    "os_version": "RHEL 9.5 → RHEL 9.6",
    "hardware": "AWS m5.xlarge"
}

# Generate analysis
analysis = analyze_performance_comparison(
    baseline_data=baseline_data,
    comparison_data=comparison_data,
    metadata=metadata,
    persona="tech_lead"  # Options: "executive", "tech_lead", "expert"
)

print(analysis)
```

#### Using Service Class

```python
from src.ai_analysis import AIAnalysisService

# Initialize service
service = AIAnalysisService(api_key="your-key-here")

# Check availability
if service.is_available():
    # Perform analysis
    result = service.analyze_comparison(
        baseline_data=baseline_data,
        comparison_data=comparison_data,
        metadata=metadata,
        persona="executive"
    )
```

#### Dashboard Integration

```python
from src.components.summaries import generate_ai_analysis, summarize_investigation_details

# Generate investigation summary
summary = summarize_investigation_details(
    baseline_df=baseline_df,
    comparison_df=comparison_df,
    test_name="benchmark_xyz",
    baseline_label="RHEL 9.5",
    comparison_label="RHEL 9.6"
)

# Generate AI analysis (returns None if AI unavailable)
ai_analysis = generate_ai_analysis(summary, persona="tech_lead")

if ai_analysis:
    print(ai_analysis)
else:
    print("AI analysis not available")
```

### Persona Prompt System

The system uses structured prompt templates defined in `src/persona_prompts.py`:

```python
from src.persona_prompts import get_persona_prompt, get_available_personas

# List available personas
personas = get_available_personas()
# Returns: [
#   {"id": "executive", "name": "Executive", "description": "..."},
#   {"id": "tech_lead", "name": "Technical Lead", "description": "..."},
#   {"id": "expert", "name": "Expert", "description": "..."}
# ]

# Get prompts for a specific persona
system_prompt, user_prompt = get_persona_prompt(
    persona="executive",
    comparison_context="[formatted comparison data]"
)
```

## Architecture

### Components

1. **`src/persona_prompts.py`**: Prompt template definitions
   - Defines system and user prompts for each persona
   - Formats comparison context for AI consumption
   - Validates persona types

2. **`src/ai_analysis.py`**: AI service integration
   - Wraps Anthropic Claude API
   - Handles errors and graceful degradation
   - Provides convenience functions

3. **`src/components/summaries.py`**: Dashboard integration
   - Connects investigation summaries to AI analysis
   - Formats data for AI consumption
   - Handles UI display

### Data Flow

```
Investigation Data
        ↓
summarize_investigation_details()
        ↓
Investigation Summary Dict
        ↓
generate_ai_analysis()
        ↓
format_comparison_context()
        ↓
get_persona_prompt()
        ↓
Claude API (via anthropic package)
        ↓
AI-Generated Analysis Text
        ↓
Dashboard Display
```

## Error Handling

The AI analysis system is designed to fail gracefully:

1. **Missing API Key**: Service returns `None`, features disabled
2. **API Errors**: Logged and return `None`, no UI disruption
3. **Network Issues**: Timeout and retry handled by SDK
4. **Invalid Responses**: Validated and gracefully handled

```python
from src.ai_analysis import get_ai_analysis_service, AIAnalysisError

service = get_ai_analysis_service()

if service is None:
    # API key not configured - features disabled
    print("AI analysis unavailable")
else:
    try:
        result = service.analyze_comparison(...)
    except AIAnalysisError as e:
        # Handle specific AI service errors
        print(f"Analysis failed: {e}")
```

## Performance Considerations

### API Costs

Claude API usage is billed per token. Approximate costs per analysis:

- **Executive**: ~500-800 tokens (~$0.003-0.005 per analysis)
- **Technical Lead**: ~1000-1500 tokens (~$0.006-0.010 per analysis)
- **Expert**: ~2000-3000 tokens (~$0.012-0.020 per analysis)

Costs based on Claude Sonnet 4 pricing as of 2026. Check [Anthropic Pricing](https://www.anthropic.com/pricing) for current rates.

### Caching

The system does not currently cache AI responses. Each analysis triggers a new API call. Consider implementing caching if:
- Same comparisons are analyzed frequently
- API costs become significant
- Response time needs optimization

### Rate Limits

Anthropic API has rate limits based on your plan:
- **Free tier**: 50 requests/minute
- **Paid tiers**: Higher limits based on plan

The service handles rate limit errors gracefully. For high-volume usage, consider:
- Request queuing
- Exponential backoff
- Tier upgrade

## Testing

### Unit Tests

```bash
# Run all AI analysis tests
pytest tests/test_persona_prompts.py tests/test_ai_analysis.py -v

# Run specific test
pytest tests/test_ai_analysis.py::test_analyze_comparison_success -v
```

### Integration Tests

The tests use mocked Anthropic API responses. To test with real API:

```python
import os
from src.ai_analysis import AIAnalysisService

# Set real API key
service = AIAnalysisService(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Run test analysis
result = service.analyze_comparison(
    baseline_data={"metric": 100},
    comparison_data={"metric": 120},
    persona="executive"
)
print(result)
```

## Future Enhancements

Potential improvements for future iterations:

1. **Batch Analysis**: Analyze multiple comparisons in one request
2. **Trend Detection**: Multi-point temporal analysis
3. **Recommendation Engine**: Specific tuning suggestions
4. **Custom Personas**: User-defined persona templates
5. **Analysis History**: Track and compare AI insights over time
6. **Confidence Scoring**: AI-generated confidence levels
7. **Interactive Refinement**: Follow-up questions and clarifications

## Troubleshooting

### Common Issues

**Issue**: "AI analysis service unavailable"
- **Cause**: ANTHROPIC_API_KEY not set or invalid
- **Solution**: Check `.env` file and verify API key

**Issue**: "anthropic package not installed"
- **Cause**: Missing Python package
- **Solution**: `pip install anthropic>=0.39.0`

**Issue**: "API error: rate limit exceeded"
- **Cause**: Too many requests
- **Solution**: Wait and retry, or upgrade plan

**Issue**: AI analysis returns None
- **Cause**: API error or missing configuration
- **Solution**: Check logs for specific error message

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('src.ai_analysis')
logger.setLevel(logging.DEBUG)
```

## Security

### API Key Management

**Best Practices:**
1. Never commit API keys to version control
2. Use `.env` files (ignored by git)
3. Rotate keys regularly
4. Use environment variables in production
5. Limit key permissions if possible

### Data Privacy

- Performance data is sent to Anthropic's API
- Review Anthropic's [Data Privacy Policy](https://www.anthropic.com/privacy)
- For sensitive data, consider:
  - On-premise AI models
  - Data sanitization before analysis
  - Aggregated metrics only

## References

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Model Specifications](https://docs.anthropic.com/en/docs/models-overview)
- [Python SDK Documentation](https://github.com/anthropics/anthropic-sdk-python)

## Support

For issues or questions:
1. Check this documentation
2. Review test files for usage examples
3. Check Anthropic API status
4. Open an issue in the project repository
