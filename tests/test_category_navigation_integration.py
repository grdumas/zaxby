"""Integration tests for end-to-end category navigation workflow (P1-C)."""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.benchmark_categories import category_for_test_name, benchmark_groups
from app import (
    competitive_performance_breadcrumb,
    investigation_drill_breadcrumb,
)


class TestCategoryBrowseToLeafWorkflow:
    """Test complete workflow from category browse to leaf benchmark view."""

    def test_category_resolution_to_navigation(self):
        """Test that category mapping flows correctly into navigation."""
        # Step 1: Resolve category for a benchmark
        test_name = "uperf"
        category = category_for_test_name(test_name)
        assert category == "Networking"

        # Step 2: Create competitive performance breadcrumb
        comp_bc = competitive_performance_breadcrumb(category)
        assert comp_bc.items[1]["label"] == "Networking"

        # Step 3: Drill down to investigation view
        inv_bc = investigation_drill_breadcrumb(category, test_name)
        assert len(inv_bc.items) == 3
        assert inv_bc.items[1]["label"] == category
        assert inv_bc.items[2]["label"] == test_name

    def test_multiple_benchmarks_in_category(self):
        """Test navigation for category with multiple benchmarks."""
        # HPC/Compute has multiple benchmarks
        category = "HPC/Compute"
        groups = benchmark_groups()
        benchmarks = groups.get(category, [])

        assert len(benchmarks) > 1  # Should have multiple benchmarks

        # Each benchmark should navigate correctly
        for benchmark in benchmarks:
            bc = investigation_drill_breadcrumb(category, benchmark)
            assert len(bc.items) == 3
            assert bc.items[1]["label"] == category
            assert bc.items[2]["label"] == benchmark

    def test_category_filter_workflow(self):
        """Test workflow of filtering data by category."""
        # Create mock comparison data
        data = {
            'test.name': ['uperf', 'fio', 'streams', 'coremark'],
            'relative_performance': [105.0, 95.0, 110.0, 98.0],
            'hardware_type': ['aws.m6i.2xlarge', 'azure.d4s_v3', 'gcp.n2.4', 'aws.c6i.large']
        }
        df = pd.DataFrame(data)

        # Add category column
        df['benchmark_category'] = df['test.name'].apply(category_for_test_name)

        # Filter to a specific category
        category = "Networking"
        category_df = df[df['benchmark_category'] == category]

        assert len(category_df) == 1
        assert category_df.iloc[0]['test.name'] == 'uperf'

        # Verify navigation for filtered data
        bc = competitive_performance_breadcrumb(category)
        assert bc.items[1]["label"] == category

    def test_unmapped_benchmark_workflow(self):
        """Test workflow for unmapped benchmark (should go to 'Other' category)."""
        test_name = "unknown_benchmark"
        category = category_for_test_name(test_name)
        assert category == "Other"

        # Navigation should still work
        bc = investigation_drill_breadcrumb(category, test_name)
        assert len(bc.items) == 3
        assert bc.items[1]["label"] == "Other"
        assert bc.items[2]["label"] == test_name

    def test_empty_category_workflow(self):
        """Test workflow when category has no data (edge case)."""
        # Create empty dataframe with correct structure
        empty_df = pd.DataFrame(columns=['test.name', 'benchmark_category', 'relative_performance'])

        # Filter to category should return empty
        category_df = empty_df[empty_df['benchmark_category'] == 'Networking']
        assert len(category_df) == 0

        # Navigation should still render correctly
        bc = competitive_performance_breadcrumb("Networking")
        assert len(bc.items) == 2
        assert bc.items[1]["label"] == "Networking"

    def test_single_benchmark_category_workflow(self):
        """Test workflow for category with single benchmark."""
        # Networking has only one benchmark: uperf
        groups = benchmark_groups()
        networking_benchmarks = groups.get("Networking", [])
        assert len(networking_benchmarks) == 1
        assert "uperf" in networking_benchmarks

        # Create data for this category
        data = {
            'test.name': ['uperf'],
            'relative_performance': [105.0],
            'hardware_type': ['aws.m6i.2xlarge']
        }
        df = pd.DataFrame(data)
        df['benchmark_category'] = df['test.name'].apply(category_for_test_name)

        # Filter to category
        category_df = df[df['benchmark_category'] == 'Networking']
        assert len(category_df) == 1

        # Navigation from category to benchmark
        bc = investigation_drill_breadcrumb("Networking", "uperf")
        assert len(bc.items) == 3
        assert bc.items[1]["label"] == "Networking"
        assert bc.items[2]["label"] == "uperf"


class TestCategoryDetailPanelDataFlow:
    """Test data flow for category detail panel."""

    def test_category_data_extraction(self):
        """Test extracting category-specific data from comparison results."""
        # Create mock comparison data with multiple categories
        data = {
            'test.name': ['uperf', 'fio', 'streams', 'auto_hpl', 'coremark'],
            'relative_performance': [105.0, 95.0, 110.0, 102.0, 98.0],
            'hardware_type': ['aws.m6i.2xlarge', 'azure.d4s_v3', 'gcp.n2.4', 'aws.c6i.large', 'azure.e4s_v3']
        }
        df = pd.DataFrame(data)
        df['benchmark_category'] = df['test.name'].apply(category_for_test_name)

        # Extract data for HPC/Compute category
        category = "HPC/Compute"
        category_df = df[df['benchmark_category'] == category]

        # Should have 2 benchmarks: streams and auto_hpl
        assert len(category_df) == 2
        assert set(category_df['test.name']) == {'streams', 'auto_hpl'}

        # Verify statistics can be computed
        avg_performance = category_df['relative_performance'].mean()
        assert avg_performance == pytest.approx(106.0)

    def test_category_summary_statistics(self):
        """Test computing summary statistics for category detail panel."""
        data = {
            'test.name': ['fio', 'fio', 'fio'],
            'relative_performance': [95.0, 105.0, 100.0],
            'hardware_type': ['hw1', 'hw2', 'hw3']
        }
        df = pd.DataFrame(data)
        df['benchmark_category'] = df['test.name'].apply(category_for_test_name)

        category_df = df[df['benchmark_category'] == 'Storage/IO']

        # Summary stats
        num_benchmarks = category_df['test.name'].nunique()
        num_hardware = category_df['hardware_type'].nunique()
        avg_perf = category_df['relative_performance'].mean()

        assert num_benchmarks == 1  # Only fio
        assert num_hardware == 3
        assert avg_perf == pytest.approx(100.0)

    def test_cross_category_isolation(self):
        """Test that category filtering properly isolates data."""
        data = {
            'test.name': ['uperf', 'fio', 'streams'],
            'relative_performance': [105.0, 95.0, 110.0],
        }
        df = pd.DataFrame(data)
        df['benchmark_category'] = df['test.name'].apply(category_for_test_name)

        # Each category should only see its own data
        networking_df = df[df['benchmark_category'] == 'Networking']
        storage_df = df[df['benchmark_category'] == 'Storage/IO']
        hpc_df = df[df['benchmark_category'] == 'HPC/Compute']

        assert len(networking_df) == 1
        assert networking_df.iloc[0]['test.name'] == 'uperf'

        assert len(storage_df) == 1
        assert storage_df.iloc[0]['test.name'] == 'fio'

        assert len(hpc_df) == 1
        assert hpc_df.iloc[0]['test.name'] == 'streams'


class TestCategoryHierarchyConsistency:
    """Test consistency of category hierarchy across different views."""

    def test_category_consistency_across_views(self):
        """Test that category labels are consistent across all navigation points."""
        test_cases = [
            ("uperf", "Networking"),
            ("fio", "Storage/IO"),
            ("streams", "HPC/Compute"),
            ("coremark", "System"),
        ]

        for test_name, expected_category in test_cases:
            # Category resolution
            category = category_for_test_name(test_name)
            assert category == expected_category

            # Competitive performance breadcrumb
            comp_bc = competitive_performance_breadcrumb(category)
            assert comp_bc.items[1]["label"] == expected_category

            # Investigation breadcrumb
            inv_bc = investigation_drill_breadcrumb(category, test_name)
            assert inv_bc.items[1]["label"] == expected_category

    def test_all_benchmarks_have_category_path(self):
        """Test that all benchmarks in the mapping have valid navigation paths."""
        groups = benchmark_groups()

        for category, benchmarks in groups.items():
            for benchmark in benchmarks:
                # Each should have valid navigation
                bc = investigation_drill_breadcrumb(category, benchmark)
                assert len(bc.items) == 3
                assert bc.items[0]["label"] == "RHEL Regression Analysis"
                assert bc.items[1]["label"] == category
                assert bc.items[2]["label"] == benchmark

    def test_category_roundtrip(self):
        """Test that category → benchmark → category resolution is consistent."""
        groups = benchmark_groups()

        for expected_category, benchmarks in groups.items():
            for benchmark in benchmarks:
                # Resolve category from benchmark
                resolved_category = category_for_test_name(benchmark)
                # Should match the original category
                assert resolved_category == expected_category


class TestCategoryNavigationEdgeCases:
    """Test edge cases in category navigation."""

    def test_benchmark_name_with_special_characters(self):
        """Test navigation with special characters in benchmark names."""
        # Even with special chars, navigation should work
        special_names = [
            "test-with-dashes",
            "test_with_underscores",
            "test.with.dots",
            "test:with:colons",
        ]

        for name in special_names:
            category = category_for_test_name(name)  # Will be "Other"
            bc = investigation_drill_breadcrumb(category, name)
            assert len(bc.items) == 3
            assert bc.items[2]["label"] == name

    def test_empty_benchmark_name(self):
        """Test navigation with empty benchmark name."""
        category = category_for_test_name("")
        assert category == "Other"

        # Navigation should still work (though unusual)
        bc = investigation_drill_breadcrumb(category, "")
        assert len(bc.items) == 3
        assert bc.items[2]["label"] == ""

    def test_none_benchmark_name(self):
        """Test navigation with None benchmark name."""
        category = category_for_test_name(None)
        assert category == "Other"

    def test_case_sensitivity_in_navigation(self):
        """Test that case variations in benchmark names resolve correctly."""
        # category_for_test_name is case-insensitive
        assert category_for_test_name("uperf") == "Networking"
        assert category_for_test_name("UPERF") == "Networking"
        assert category_for_test_name("UPerf") == "Networking"

        # Navigation should work with any case
        for variant in ["uperf", "UPERF", "UPerf"]:
            category = category_for_test_name(variant)
            bc = investigation_drill_breadcrumb(category, variant)
            assert bc.items[1]["label"] == "Networking"
            assert bc.items[2]["label"] == variant  # Original case preserved in breadcrumb
