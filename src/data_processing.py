"""
Data processing and transformation logic for benchmark results.

Handles conversion of raw OpenSearch/synthetic data into formats
suitable for visualization and analysis.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkDataProcessor:
    """Process and transform benchmark results for visualization."""
    
    def __init__(self):
        """Initialize the data processor."""
        pass
    
    def documents_to_dataframe(self, documents: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of document dictionaries to a pandas DataFrame.
        
        Args:
            documents: List of benchmark result documents
            
        Returns:
            DataFrame with flattened and processed fields
        """
        if not documents:
            return pd.DataFrame()
        
        records = []
        for doc in documents:
            try:
                record = self._extract_record(doc)
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to process document: {e}")
                continue
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        logger.info(f"Processed {len(df)} documents into DataFrame")
        return df
    
    def _extract_record(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a flat record from a nested document.
        
        Args:
            doc: Benchmark result document
            
        Returns:
            Flattened dictionary of key fields
        """
        metadata = doc.get('metadata', {})
        test = doc.get('test', {})
        system = doc.get('system_under_test', {})
        os_info = system.get('operating_system', {})
        hardware = system.get('hardware', {})
        cpu = hardware.get('cpu', {})
        results = doc.get('results', {})
        primary_metric = results.get('primary_metric', {})
        
        # Extract run metrics if available
        runs = results.get('runs', {})
        run_0_metrics = {}
        if runs:
            first_run_key = list(runs.keys())[0]
            run_0_metrics = runs[first_run_key].get('metrics', {})
        
        record = {
            # Identifiers
            'document_id': metadata.get('document_id'),
            'test_name': test.get('name'),
            'test_version': test.get('version'),
            
            # Temporal
            'timestamp': metadata.get('test_timestamp'),
            
            # System Configuration
            'os_vendor': metadata.get('os_vendor'),
            'os_distribution': os_info.get('distribution'),
            'os_version': os_info.get('version'),
            'kernel_version': os_info.get('kernel_version'),
            
            # Hardware
            'cloud_provider': metadata.get('cloud_provider'),
            'instance_type': metadata.get('instance_type'),
            'cpu_model': cpu.get('model'),
            'cpu_cores': cpu.get('cores'),
            'cpu_architecture': cpu.get('architecture'),
            'memory_gb': hardware.get('memory', {}).get('total_gb'),
            
            # Test Configuration
            'scenario_name': metadata.get('scenario_name'),
            'iteration': metadata.get('iteration'),
            
            # Results
            'status': results.get('status'),
            'primary_metric_name': primary_metric.get('name'),
            'primary_metric_value': primary_metric.get('value'),
            'primary_metric_unit': primary_metric.get('unit'),
        }
        
        # Add additional metrics from run_0 (flatten key ones)
        # Only add if they don't conflict with existing keys
        for key, value in run_0_metrics.items():
            if key not in record and isinstance(value, (int, float)):
                record[f'metric_{key}'] = value
        
        return record
    
    def filter_data(
        self,
        df: pd.DataFrame,
        os_versions: Optional[List[str]] = None,
        instance_types: Optional[List[str]] = None,
        test_names: Optional[List[str]] = None,
        cloud_providers: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        status_filter: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter DataFrame based on multiple criteria.
        
        Args:
            df: Input DataFrame
            os_versions: List of OS versions to include
            instance_types: List of instance types to include
            test_names: List of test names to include
            cloud_providers: List of cloud providers to include
            date_range: Tuple of (start_date, end_date)
            status_filter: List of status values to include
            
        Returns:
            Filtered DataFrame
        """
        filtered = df.copy()
        
        if os_versions:
            filtered = filtered[filtered['os_version'].isin(os_versions)]
        
        if instance_types:
            filtered = filtered[filtered['instance_type'].isin(instance_types)]
        
        if test_names:
            filtered = filtered[filtered['test_name'].isin(test_names)]
        
        if cloud_providers:
            filtered = filtered[filtered['cloud_provider'].isin(cloud_providers)]
        
        if status_filter:
            filtered = filtered[filtered['status'].isin(status_filter)]
        
        if date_range and 'timestamp' in filtered.columns:
            start_date, end_date = date_range
            filtered = filtered[
                (filtered['timestamp'] >= start_date) &
                (filtered['timestamp'] <= end_date)
            ]
        
        logger.info(f"Filtered from {len(df)} to {len(filtered)} records")
        return filtered
    
    def calculate_comparison(
        self,
        df: pd.DataFrame,
        baseline_filters: Dict[str, Any],
        comparison_filters: Dict[str, Any],
        group_by: str = 'test_name'
    ) -> pd.DataFrame:
        """
        Calculate performance comparison between two configurations.
        
        Args:
            df: Input DataFrame
            baseline_filters: Filters to select baseline data
            comparison_filters: Filters to select comparison data
            group_by: Field to group results by
            
        Returns:
            DataFrame with comparison statistics
        """
        # Filter baseline and comparison data
        baseline_df = self.filter_data(df, **baseline_filters)
        comparison_df = self.filter_data(df, **comparison_filters)
        
        # Group and aggregate
        baseline_agg = baseline_df.groupby(group_by).agg({
            'primary_metric_value': ['mean', 'std', 'count']
        }).reset_index()
        baseline_agg.columns = [group_by, 'baseline_mean', 'baseline_std', 'baseline_count']
        
        comparison_agg = comparison_df.groupby(group_by).agg({
            'primary_metric_value': ['mean', 'std', 'count']
        }).reset_index()
        comparison_agg.columns = [group_by, 'comparison_mean', 'comparison_std', 'comparison_count']
        
        # Merge and calculate differences
        result = baseline_agg.merge(comparison_agg, on=group_by, how='outer')
        
        result['delta'] = result['comparison_mean'] - result['baseline_mean']
        result['percent_change'] = (
            (result['comparison_mean'] - result['baseline_mean']) / 
            result['baseline_mean'] * 100
        )
        
        # Classify change magnitude
        result['change_category'] = result['percent_change'].apply(
            lambda x: 'Regression' if x < -10 else (
                'Improvement' if x > 10 else 'Stable'
            )
        )
        
        return result
    
    def aggregate_by_time(
        self,
        df: pd.DataFrame,
        time_freq: str = 'D',
        agg_func: str = 'mean'
    ) -> pd.DataFrame:
        """
        Aggregate metrics by time period.
        
        Args:
            df: Input DataFrame
            time_freq: Pandas time frequency ('D'=day, 'W'=week, 'M'=month)
            agg_func: Aggregation function ('mean', 'median', 'max', 'min')
            
        Returns:
            Time-aggregated DataFrame
        """
        if 'timestamp' not in df.columns:
            logger.warning("No timestamp column found")
            return df
        
        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)
        
        numeric_cols = df_copy.select_dtypes(include=['float64', 'int64']).columns
        
        aggregated = df_copy[numeric_cols].resample(time_freq).agg(agg_func)
        aggregated.reset_index(inplace=True)
        
        return aggregated
    
    def get_unique_values(self, df: pd.DataFrame, column: str) -> List[Any]:
        """
        Get sorted list of unique values in a column.
        
        Args:
            df: Input DataFrame
            column: Column name
            
        Returns:
            Sorted list of unique values
        """
        if column not in df.columns:
            return []
        
        unique_vals = df[column].dropna().unique().tolist()
        try:
            return sorted(unique_vals)
        except TypeError:
            return unique_vals
    
    def create_regression_matrix(
        self,
        df: pd.DataFrame,
        row_dimension: str = 'os_version',
        col_dimension: str = 'instance_type',
        metric: str = 'primary_metric_value'
    ) -> pd.DataFrame:
        """
        Create a heatmap matrix for regression analysis.
        
        Args:
            df: Input DataFrame
            row_dimension: Field to use for rows
            col_dimension: Field to use for columns
            metric: Metric to aggregate
            
        Returns:
            Pivot table suitable for heatmap visualization
        """
        pivot = df.pivot_table(
            values=metric,
            index=row_dimension,
            columns=col_dimension,
            aggfunc='mean'
        )
        
        return pivot
    
    def calculate_statistics(
        self,
        df: pd.DataFrame,
        group_by: List[str],
        metric: str = 'primary_metric_value'
    ) -> pd.DataFrame:
        """
        Calculate detailed statistics for groups.
        
        Args:
            df: Input DataFrame
            group_by: List of columns to group by
            metric: Metric column to analyze
            
        Returns:
            DataFrame with statistics
        """
        if metric not in df.columns:
            logger.warning(f"Metric '{metric}' not found in DataFrame")
            return pd.DataFrame()
        
        stats = df.groupby(group_by)[metric].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('median', 'median'),
            ('std', 'std'),
            ('min', 'min'),
            ('max', 'max'),
            ('q25', lambda x: x.quantile(0.25)),
            ('q75', lambda x: x.quantile(0.75))
        ]).reset_index()
        
        # Calculate coefficient of variation
        stats['cv'] = (stats['std'] / stats['mean'] * 100).round(2)
        
        return stats
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        metric: str = 'primary_metric_value',
        method: str = 'iqr',
        threshold: float = 1.5
    ) -> pd.DataFrame:
        """
        Detect outliers in the data.
        
        Args:
            df: Input DataFrame
            metric: Metric column to check
            method: Detection method ('iqr' or 'zscore')
            threshold: Threshold for outlier detection
            
        Returns:
            DataFrame with outlier flag added
        """
        if metric not in df.columns:
            return df
        
        df_copy = df.copy()
        
        if method == 'iqr':
            Q1 = df_copy[metric].quantile(0.25)
            Q3 = df_copy[metric].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            df_copy['is_outlier'] = (
                (df_copy[metric] < lower_bound) | 
                (df_copy[metric] > upper_bound)
            )
        elif method == 'zscore':
            mean = df_copy[metric].mean()
            std = df_copy[metric].std()
            df_copy['is_outlier'] = (
                abs((df_copy[metric] - mean) / std) > threshold
            )
        
        outlier_count = df_copy['is_outlier'].sum()
        logger.info(f"Detected {outlier_count} outliers using {method} method")
        
        return df_copy


def load_synthetic_data(filepath: str = "data/synthetic/benchmark_results.json") -> List[Dict[str, Any]]:
    """
    Load synthetic data from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        List of document dictionaries
    """
    import json
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data)} documents from {filepath}")
    return data


def main():
    """Test the data processing functionality."""
    
    print("Testing BenchmarkDataProcessor")
    print("=" * 60)
    
    # Load synthetic data
    print("\n1. Loading synthetic data...")
    documents = load_synthetic_data()
    print(f"   Loaded {len(documents)} documents")
    
    # Initialize processor
    processor = BenchmarkDataProcessor()
    
    # Convert to DataFrame
    print("\n2. Converting to DataFrame...")
    df = processor.documents_to_dataframe(documents)
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {list(df.columns[:10])}...")
    
    # Show unique values for key dimensions
    print("\n3. Filter Dimensions:")
    print(f"   OS Versions: {processor.get_unique_values(df, 'os_version')}")
    print(f"   Instance Types: {processor.get_unique_values(df, 'instance_type')[:5]}...")
    print(f"   Test Types: {processor.get_unique_values(df, 'test_name')}")
    print(f"   Cloud Providers: {processor.get_unique_values(df, 'cloud_provider')}")
    
    # Calculate statistics
    print("\n4. Statistics by Test Type:")
    stats = processor.calculate_statistics(
        df,
        group_by=['test_name'],
        metric='primary_metric_value'
    )
    print(stats.to_string(index=False))
    
    # Test filtering
    print("\n5. Testing filters...")
    filtered = processor.filter_data(
        df,
        os_versions=['9.5'],
        test_names=['coremark', 'streams']
    )
    print(f"   Filtered to {len(filtered)} records (OS 9.5, CoreMark/STREAM only)")
    
    # Test comparison
    print("\n6. Testing comparison (RHEL 9.5 vs 9.4)...")
    if len(df[df['os_version'] == '9.5']) > 0 and len(df[df['os_version'] == '9.4']) > 0:
        comparison = processor.calculate_comparison(
            df,
            baseline_filters={'os_versions': ['9.4']},
            comparison_filters={'os_versions': ['9.5']},
            group_by='test_name'
        )
        print(comparison[['test_name', 'baseline_mean', 'comparison_mean', 'percent_change', 'change_category']].to_string(index=False))
    else:
        print("   Insufficient data for comparison")
    
    print("\n✓ Data processing tests complete!")


if __name__ == "__main__":
    main()

