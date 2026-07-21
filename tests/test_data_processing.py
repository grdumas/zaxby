"""
Tests for data processing module.
"""

import pytest
import pandas as pd
from src.data_processing import BenchmarkDataProcessor, _first_document_id


@pytest.fixture
def processor():
    """Create a BenchmarkDataProcessor instance."""
    return BenchmarkDataProcessor()


@pytest.fixture
def sample_documents():
    """Create sample benchmark documents."""
    return [
        {
            "metadata": {
                "document_id": "test_1",
                "test_timestamp": "2025-11-01T10:00:00Z",
                "os_vendor": "rhel",
                "cloud_provider": "aws",
                "instance_type": "m5.24xlarge",
                "scenario_name": "test_scenario"
            },
            "test": {
                "name": "coremark",
                "version": "v1.0"
            },
            "system_under_test": {
                "hardware": {
                    "cpu": {
                        "model": "Intel Xeon",
                        "cores": 96,
                        "architecture": "x86_64"
                    },
                    "memory": {
                        "total_gb": 373
                    }
                },
                "operating_system": {
                    "distribution": "rhel",
                    "version": "9.5",
                    "kernel_version": "5.14.0"
                }
            },
            "results": {
                "status": "PASS",
                "primary_metric": {
                    "name": "score",
                    "value": 500000.0,
                    "unit": "BOPs"
                },
                "runs": {
                    "run_0": {
                        "metrics": {
                            "multicore_score": 500000.0,
                            "singlecore_score": 5000.0
                        }
                    }
                }
            }
        },
        {
            "metadata": {
                "document_id": "test_2",
                "test_timestamp": "2025-11-02T10:00:00Z",
                "os_vendor": "rhel",
                "cloud_provider": "aws",
                "instance_type": "m5.24xlarge",
                "scenario_name": "test_scenario"
            },
            "test": {
                "name": "streams",
                "version": "v1.0"
            },
            "system_under_test": {
                "hardware": {
                    "cpu": {
                        "model": "Intel Xeon",
                        "cores": 96,
                        "architecture": "x86_64"
                    },
                    "memory": {
                        "total_gb": 373
                    }
                },
                "operating_system": {
                    "distribution": "rhel",
                    "version": "9.4",
                    "kernel_version": "5.14.0"
                }
            },
            "results": {
                "status": "PASS",
                "primary_metric": {
                    "name": "bandwidth",
                    "value": 180000.0,
                    "unit": "MB/s"
                },
                "runs": {
                    "run_0": {
                        "metrics": {
                            "copy_mb_per_sec": 180000.0
                        }
                    }
                }
            }
        }
    ]


def test_documents_to_dataframe(processor, sample_documents):
    """Test conversion of documents to DataFrame."""
    df = processor.documents_to_dataframe(sample_documents)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert 'test_name' in df.columns
    assert 'os_version' in df.columns
    assert 'primary_metric_value' in df.columns


def test_documents_to_dataframe_empty(processor):
    """Test with empty document list."""
    df = processor.documents_to_dataframe([])
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_filter_data(processor, sample_documents):
    """Test data filtering."""
    df = processor.documents_to_dataframe(sample_documents)
    
    # Filter by OS version
    filtered = processor.filter_data(df, os_versions=['9.5'])
    assert len(filtered) == 1
    assert filtered['os_version'].iloc[0] == '9.5'
    
    # Filter by test name
    filtered = processor.filter_data(df, test_names=['coremark'])
    assert len(filtered) == 1
    assert filtered['test_name'].iloc[0] == 'coremark'


def test_get_unique_values(processor, sample_documents):
    """Test extraction of unique values."""
    df = processor.documents_to_dataframe(sample_documents)
    
    os_versions = processor.get_unique_values(df, 'os_version')
    assert set(os_versions) == {'9.4', '9.5'}
    
    test_names = processor.get_unique_values(df, 'test_name')
    assert set(test_names) == {'coremark', 'streams'}


def test_calculate_statistics(processor, sample_documents):
    """Test statistics calculation."""
    df = processor.documents_to_dataframe(sample_documents)
    
    stats = processor.calculate_statistics(df, group_by=['test_name'])
    
    assert isinstance(stats, pd.DataFrame)
    assert 'count' in stats.columns
    assert 'mean' in stats.columns
    assert 'std' in stats.columns
    assert len(stats) == 2  # Two test types


def test_detect_outliers(processor, sample_documents):
    """Test outlier detection."""
    df = processor.documents_to_dataframe(sample_documents)
    
    df_with_outliers = processor.detect_outliers(df, method='iqr')
    
    assert 'is_outlier' in df_with_outliers.columns
    assert df_with_outliers['is_outlier'].dtype == bool


def test_extract_record_missing_fields(processor):
    """Test record extraction with missing fields."""
    incomplete_doc = {
        "metadata": {"document_id": "test_3"},
        "test": {},
        "results": {}
    }
    
    record = processor._extract_record(incomplete_doc)
    
    assert isinstance(record, dict)
    assert record['document_id'] == 'test_3'
    assert 'test_name' in record
    assert 'status' in record


def test_extract_record_primary_metric_fallback_from_runs(processor):
    """When primary_metric is absent, use known run metric keys (live Zathras data)."""
    doc = {
        "metadata": {
            "document_id": "z1",
            "test_timestamp": "2025-11-01T10:00:00Z",
            "os_vendor": "rhel",
            "cloud_provider": "aws",
            "instance_type": "m5.4xlarge",
        },
        "test": {"name": "coremark", "version": "v1"},
        "system_under_test": {
            "hardware": {"cpu": {"cores": 16}, "memory": {"total_gb": 64}},
            "operating_system": {
                "distribution": "rhel",
                "version": "9.8",
            },
        },
        "results": {
            "status": "PASS",
            "runs": {
                "run_0": {
                    "metrics": {
                        "iterations_per_second": 123456.0,
                    }
                }
            },
        },
    }
    record = processor._extract_record(doc)
    assert record["primary_metric_value"] == 123456.0
    assert record["primary_metric_name"] == "iterations_per_second"


def test_first_document_id_empty():
    assert _first_document_id(pd.DataFrame()) is None


def test_first_document_id_missing_column():
    df = pd.DataFrame({"a": [1]})
    assert _first_document_id(df) is None


def test_first_document_id_first_non_null():
    df = pd.DataFrame({"document_id": [None, "x", "y"]})
    assert _first_document_id(df) == "x"


def test_compare_two_versions_propagates_document_ids(processor):
    """Aggregated comparison rows carry representative document_ids for Discover."""
    df = pd.DataFrame(
        [
            {
                "os_version": "9.0",
                "test_name": "coremark",
                "cloud_provider": "aws",
                "instance_type": "m5.xlarge",
                "primary_metric_value": 100.0,
                "benchmark_category": "cpu",
                "document_id": "doc-b1",
                "status": "PASS",
            },
            {
                "os_version": "10.0",
                "test_name": "coremark",
                "cloud_provider": "aws",
                "instance_type": "m5.xlarge",
                "primary_metric_value": 80.0,
                "benchmark_category": "cpu",
                "document_id": "doc-c1",
                "status": "PASS",
            },
        ]
    )
    out = processor._compare_two_versions(df, "9.0", "10.0", -5.0, label="t")
    comp = out["comparison_data"]
    assert not comp.empty
    row = comp.iloc[0]
    assert row["baseline_document_id"] == "doc-b1"
    assert row["comparison_document_id"] == "doc-c1"


def test_analyze_os_version_regressions_empty_comparison_matrix_no_keyerror(processor):
    """
    When no test×version pair yields both baseline and current rows, comparison_results
    is empty; DataFrame has no columns and must not index ``is_regression`` without a guard.
    """
    df = pd.DataFrame(
        [
            {
                "os_distribution": "rhel",
                "os_version": "9.0",
                "test_name": "coremark",
                "primary_metric_value": 100.0,
                "status": "PASS",
            },
            {
                "os_distribution": "rhel",
                "os_version": "9.1",
                "test_name": "streams",
                "primary_metric_value": 200.0,
                "status": "PASS",
            },
        ]
    )
    out = processor.analyze_os_version_regressions(
        df, os_distribution="rhel", os_versions=["9.0", "9.1"]
    )
    assert out["comparison_data"].empty
    assert out["num_regressions"] == 0
    assert out["regressions"] == []


# Cloud Scaling Analysis Tests


@pytest.fixture
def cloud_scaling_data():
    """Create sample data for cloud scaling analysis."""
    return pd.DataFrame([
        {
            "cloud_provider": "gcp",
            "os_version": "10.1",
            "instance_type": "c2-standard-4",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 4,
            "memory_gb": 16,
            "primary_metric_value": 100000.0,
            "std_performance": 1000.0
        },
        {
            "cloud_provider": "gcp",
            "os_version": "10.1",
            "instance_type": "c2-standard-8",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 8,
            "memory_gb": 32,
            "primary_metric_value": 195000.0,  # ~97.5% linear scaling
            "std_performance": 2000.0
        },
        {
            "cloud_provider": "gcp",
            "os_version": "10.1",
            "instance_type": "c2-standard-16",
            "test_name": "coremark",
            "benchmark_category": "CPU",
            "cpu_cores": 16,
            "memory_gb": 64,
            "primary_metric_value": 380000.0,  # ~95% linear scaling
            "std_performance": 3000.0
        },
        {
            "cloud_provider": "gcp",
            "os_version": "10.1",
            "instance_type": "c2-standard-4",
            "test_name": "streams",
            "benchmark_category": "Memory",
            "cpu_cores": 4,
            "memory_gb": 16,
            "primary_metric_value": 50000.0,
            "std_performance": 500.0
        },
        {
            "cloud_provider": "gcp",
            "os_version": "10.1",
            "instance_type": "c2-standard-8",
            "test_name": "streams",
            "benchmark_category": "Memory",
            "cpu_cores": 8,
            "memory_gb": 32,
            "primary_metric_value": 65000.0,  # ~65% linear scaling (poor)
            "std_performance": 800.0
        },
    ])


def test_analyze_cloud_scaling_basic(processor, cloud_scaling_data):
    """Test basic cloud scaling analysis."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    # Verify result structure
    assert "scaling_data" in result
    assert "summary" in result
    assert "linear_scaling_count" in result
    assert "total_benchmarks" in result

    # Verify scaling data is not empty
    assert not result["scaling_data"].empty
    assert len(result["scaling_data"]) > 0


def test_analyze_cloud_scaling_detects_linear_scaling(processor, cloud_scaling_data):
    """Test that linear scaling is correctly detected (>85% efficiency)."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    # CoreMark should show linear scaling (~95% efficiency)
    assert result["linear_scaling_count"] >= 1
    assert result["total_benchmarks"] == 2  # coremark and streams


def test_analyze_cloud_scaling_detects_poor_scaling(processor, cloud_scaling_data):
    """Test that poor scaling is detected and reported (<70% efficiency)."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    # STREAM has poor scaling (~65%), should be in summary
    assert "streams" in result["summary"].lower() or "diminishing" in result["summary"].lower()


def test_analyze_cloud_scaling_includes_cpu_cores(processor, cloud_scaling_data):
    """Test that CPU cores are included in scaling data."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    scaling_df = result["scaling_data"]
    assert "cpu_cores" in scaling_df.columns
    assert scaling_df["cpu_cores"].notna().any()


def test_analyze_cloud_scaling_includes_memory(processor, cloud_scaling_data):
    """Test that memory_gb is included in scaling data (multi-dimensional)."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    scaling_df = result["scaling_data"]
    assert "memory_gb" in scaling_df.columns
    assert scaling_df["memory_gb"].notna().any()


def test_analyze_cloud_scaling_filters_by_instance_family(processor, cloud_scaling_data):
    """Test filtering by instance family."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1",
        instance_family="c2-standard"
    )

    scaling_df = result["scaling_data"]
    assert not scaling_df.empty
    # All instances should match the family filter
    assert all("c2-standard" in inst for inst in scaling_df["instance_type"].unique())


def test_analyze_cloud_scaling_empty_data(processor):
    """Test cloud scaling with no matching data."""
    # Create empty DataFrame with required columns
    empty_df = pd.DataFrame(columns=[
        'cloud_provider', 'os_version', 'instance_type', 'test_name',
        'benchmark_category', 'cpu_cores', 'memory_gb', 'primary_metric_value'
    ])

    result = processor.analyze_cloud_scaling(
        empty_df,
        cloud_provider="gcp",
        os_version="10.1"
    )

    assert result["scaling_data"].empty
    assert "No data available" in result["summary"]
    assert result["linear_scaling_count"] == 0
    assert result["total_benchmarks"] == 0


def test_analyze_cloud_scaling_instance_data_includes_cores(processor, cloud_scaling_data):
    """Test that instance data includes CPU cores for proper ordering."""
    result = processor.analyze_cloud_scaling(
        cloud_scaling_data,
        cloud_provider="gcp",
        os_version="10.1"
    )

    scaling_df = result["scaling_data"]

    # Verify all instances have CPU core data
    assert "cpu_cores" in scaling_df.columns
    assert scaling_df["cpu_cores"].notna().all()

    # Verify different instance sizes have different core counts
    core_counts = scaling_df["cpu_cores"].unique()
    assert len(core_counts) > 1  # Multiple instance sizes



