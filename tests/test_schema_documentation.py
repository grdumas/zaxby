"""
Test suite for validating SCHEMA.md documentation correctness.

This test suite ensures that the schema documentation matches actual implementation
and follows best practices for OpenSearch query examples.
"""

import re
import json
from pathlib import Path


SCHEMA_DOC_PATH = Path(__file__).parent.parent / "docs" / "guides" / "SCHEMA.md"


def test_timestamp_field_documented_as_date():
    """Test that metadata.test_timestamp is documented as 'date' type, not 'string'."""
    with open(SCHEMA_DOC_PATH) as f:
        content = f.read()

    # Find the timeseries metadata fields table
    assert "#### Key Metadata Fields" in content, (
        "Could not find '#### Key Metadata Fields' heading in SCHEMA.md"
    )
    parts = content.split("#### Key Metadata Fields")
    assert len(parts) > 1, "Expected content after '#### Key Metadata Fields' heading"
    timeseries_section = parts[1].split("####")[0]

    # Look for the test_timestamp field definition
    timestamp_line_match = re.search(
        r'\|\s*`metadata\.test_timestamp`\s*\|\s*(\w+)\s*\|',
        timeseries_section
    )

    assert timestamp_line_match, "Could not find metadata.test_timestamp field definition"

    field_type = timestamp_line_match.group(1)
    assert field_type == "date", (
        f"metadata.test_timestamp should be documented as 'date' type, not '{field_type}'. "
        "This field is used in range queries and sorting without .keyword suffix, "
        "indicating it's mapped as a date type in OpenSearch."
    )


def test_query_examples_have_appropriate_size_parameters():
    """Test that query examples include appropriate size parameters."""
    with open(SCHEMA_DOC_PATH) as f:
        content = f.read()

    # Extract the timeseries section
    timeseries_start = content.find("## Timeseries Index Schema")
    assert timeseries_start != -1, (
        "Could not find '## Timeseries Index Schema' heading in SCHEMA.md"
    )
    timeseries_end = content.find("## Dashboard Filter Dimensions", timeseries_start)
    assert timeseries_end != -1, (
        "Could not find '## Dashboard Filter Dimensions' heading after timeseries section"
    )
    timeseries_section = content[timeseries_start:timeseries_end]

    # Find all JSON code blocks in the timeseries section
    json_blocks = re.findall(r'```json\n(.*?)\n```', timeseries_section, re.DOTALL)

    issues = []
    json_errors = []

    for idx, block in enumerate(json_blocks, 1):
        try:
            query = json.loads(block)

            # Check if this is a search query (has "query" key) vs aggregation
            if "query" in query:
                # Aggregation-only queries should have size: 0
                if "aggs" in query and "size" in query and query["size"] == 0:
                    continue  # This is correct

                # Search queries should have explicit size
                if "size" not in query:
                    # Try to infer what kind of query this is from context
                    context_before = timeseries_section[:timeseries_section.find(block)]
                    last_heading = re.findall(r'####? (.+)', context_before)[-1] if re.findall(r'####? (.+)', context_before) else "unknown"

                    issues.append(
                        f"Query block {idx} (context: '{last_heading}') is missing 'size' parameter. "
                        "Queries without size default to ~10 results, which may truncate timeseries data."
                    )
        except json.JSONDecodeError as e:
            # JSON code blocks should be valid - treat decode errors as test failures
            json_errors.append(
                f"Query block {idx} contains malformed JSON: {str(e)}"
            )

    # Check for JSON errors first (more critical than missing size)
    assert not json_errors, (
        "Found malformed JSON in code blocks:\n" +
        "\n".join(f"  - {error}" for error in json_errors)
    )

    assert not issues, (
        "Found query examples missing size parameters:\n" +
        "\n".join(f"  - {issue}" for issue in issues)
    )


def test_discover_url_uses_correct_rison_format():
    """Test that Discover URL examples use the correct Rison-encoded format."""
    with open(SCHEMA_DOC_PATH) as f:
        content = f.read()

    # Find the Deep Linking section
    assert "### Deep Linking" in content, (
        "Could not find '### Deep Linking' heading in SCHEMA.md"
    )
    parts = content.split("### Deep Linking")
    assert len(parts) > 1, "Expected content after '### Deep Linking' heading"
    deep_linking_section = parts[1].split("###")[0]

    # Extract the example URL
    url_match = re.search(r'```\n(.+?)\n```', deep_linking_section, re.DOTALL)
    assert url_match, "Could not find example Discover URL"

    example_url = url_match.group(1).strip()

    # Validate it has the required Rison components
    assert "_g=" in example_url, "Discover URL should include _g parameter for time window"
    assert "_a=" in example_url, "Discover URL should include _a parameter for app state"
    assert "language:kuery" in example_url, "Discover URL should specify language:kuery"
    assert "query:" in example_url, "Discover URL should include query field"

    # Validate proper quoting in Rison format
    if "index:" in example_url:
        # Index name should be in single quotes in Rison
        assert re.search(r"index:'[^']+'", example_url), (
            "Index name should be single-quoted in Rison format (e.g., index:'zathras-timeseries')"
        )


def test_document_id_field_description_clarifies_field_based_join():
    """Test that metadata.document_id description clarifies it's a field-based join, not _id."""
    with open(SCHEMA_DOC_PATH) as f:
        content = f.read()

    # Find the timeseries metadata fields table
    assert "#### Key Metadata Fields" in content, (
        "Could not find '#### Key Metadata Fields' heading in SCHEMA.md"
    )
    parts = content.split("#### Key Metadata Fields")
    assert len(parts) > 1, "Expected content after '#### Key Metadata Fields' heading"
    timeseries_section = parts[1].split("####")[0]

    # Look for the document_id field definition
    doc_id_line_match = re.search(
        r'\|\s*`metadata\.document_id`\s*\|[^|]+\|\s*(.+?)\s*\|',
        timeseries_section
    )

    assert doc_id_line_match, "Could not find metadata.document_id field definition"

    description = doc_id_line_match.group(1)

    # The description should clarify this is NOT about OpenSearch _id
    assert "field" in description.lower() or "via" in description.lower(), (
        "metadata.document_id description should clarify that linking uses field values, "
        "not OpenSearch _id, to avoid confusion"
    )


def test_keyword_suffix_usage_is_documented():
    """Test that .keyword suffix usage is explained in the documentation."""
    with open(SCHEMA_DOC_PATH) as f:
        content = f.read()

    # Find the timeseries section
    timeseries_start = content.find("## Timeseries Index Schema")
    assert timeseries_start != -1, (
        "Could not find '## Timeseries Index Schema' heading in SCHEMA.md"
    )
    timeseries_end = content.find("## Dashboard Filter Dimensions", timeseries_start)
    assert timeseries_end != -1, (
        "Could not find '## Dashboard Filter Dimensions' heading after timeseries section"
    )
    timeseries_section = content[timeseries_start:timeseries_end]

    # Check if .keyword usage is explained
    has_keyword_note = (
        ".keyword" in timeseries_section and
        ("mapping" in timeseries_section.lower() or "exact-match" in timeseries_section.lower())
    )

    assert has_keyword_note, (
        "Documentation should include a note about when to use .keyword suffix "
        "for exact-match queries based on OpenSearch field mappings"
    )
