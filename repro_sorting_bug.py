
import pandas as pd
from src.query_service import _calculate_exception_deltas

def test_improvement_sorting():
    # Higher-is-better metric (throughput)
    # Note: src.metric_registry might need mocking or have defaults for test names
    
    baseline_df = pd.DataFrame({
        "test_name": ["test1", "test2"],
        "test_timestamp": pd.to_datetime(["2025-05-01", "2025-05-01"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [100.0, 100.0],
    })

    nightly_df = pd.DataFrame({
        "test_name": ["test1", "test2"],
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [120.0, 150.0],  # test1: +20%, test2: +50%
    })

    # We need to make sure these tests are considered higher-is-better
    # By default, most are.
    
    result = _calculate_exception_deltas(
        baseline_df, nightly_df, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    nightly_df_reg = pd.DataFrame({
        "test_name": ["test1", "test2"],
        "test_timestamp": pd.to_datetime(["2025-05-18", "2025-05-18"], utc=True),
        "status": ["PASS", "PASS"],
        "primary_metric_value": [80.0, 50.0],  # test1: -20%, test2: -50%
    })

    result_reg = _calculate_exception_deltas(
        baseline_df, nightly_df_reg, "test", max_regressions=10, max_improvements=10, max_missing=10, max_added=10
    )

    print(f"Regressions: {result_reg['regressions']}")
    # Expected for "worst first": [('test2', -50.0), ('test1', -20.0)]

if __name__ == "__main__":
    test_improvement_sorting()
