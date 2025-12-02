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
    
    # Benchmark categorization for grouping
    BENCHMARK_GROUPS = {
        'Networking': ['uperf'],
        'Storage/IO': ['fio'],
        'HPC/Compute': ['streams', 'specjbb', 'auto_hpl'],
        'System': ['sysbench', 'coremark_pro', 'pig', 'coremark', 'phoronix', 'passmark']
    }
    
    def __init__(self):
        """Initialize the data processor."""
        pass
    
    def get_benchmark_category(self, test_name: str) -> str:
        """
        Get the category for a benchmark test.
        
        Args:
            test_name: Name of the test
            
        Returns:
            Category name or 'Other'
        """
        if not test_name:
            return 'Other'
        
        test_lower = test_name.lower()
        for category, tests in self.BENCHMARK_GROUPS.items():
            if any(test.lower() in test_lower or test_lower in test.lower() for test in tests):
                return category
        return 'Other'
    
    def add_benchmark_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add benchmark category column to DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with 'benchmark_category' column added
        """
        df_copy = df.copy()
        df_copy['benchmark_category'] = df_copy['test_name'].apply(self.get_benchmark_category)
        return df_copy
    
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
    
    def analyze_os_version_regressions(
        self,
        df: pd.DataFrame,
        os_versions: Optional[List[str]] = None,
        regression_threshold: float = -5.0
    ) -> Dict[str, Any]:
        """
        Analyze performance regressions across OS versions.
        
        Args:
            df: Input DataFrame
            os_versions: List of OS versions to analyze (in order), or None for auto-detect
            regression_threshold: Percentage threshold for regression detection (negative)
            
        Returns:
            Dictionary with regression analysis results
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Auto-detect OS versions if not provided
        if not os_versions:
            os_versions = sorted(df_with_cats['os_version'].dropna().unique())
        
        if len(os_versions) < 2:
            return {
                'regressions': [],
                'summary': 'Insufficient OS versions for comparison',
                'heatmap_data': pd.DataFrame()
            }
        
        # Create comparison matrix: benchmark × OS version
        comparison_results = []
        test_names = sorted(df_with_cats['test_name'].dropna().unique())
        
        for i in range(1, len(os_versions)):
            baseline_ver = os_versions[i-1]
            current_ver = os_versions[i]
            
            for test in test_names:
                baseline_data = df_with_cats[
                    (df_with_cats['os_version'] == baseline_ver) & 
                    (df_with_cats['test_name'] == test)
                ]['primary_metric_value']
                
                current_data = df_with_cats[
                    (df_with_cats['os_version'] == current_ver) & 
                    (df_with_cats['test_name'] == test)
                ]['primary_metric_value']
                
                if len(baseline_data) > 0 and len(current_data) > 0:
                    baseline_mean = baseline_data.mean()
                    current_mean = current_data.mean()
                    pct_change = ((current_mean - baseline_mean) / baseline_mean) * 100
                    
                    comparison_results.append({
                        'test_name': test,
                        'benchmark_category': df_with_cats[df_with_cats['test_name'] == test]['benchmark_category'].iloc[0],
                        'baseline_version': baseline_ver,
                        'current_version': current_ver,
                        'baseline_mean': baseline_mean,
                        'current_mean': current_mean,
                        'percent_change': pct_change,
                        'is_regression': pct_change < regression_threshold
                    })
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # Identify regressions
        regressions = comparison_df[comparison_df['is_regression']].sort_values('percent_change')
        
        # Create heatmap data (pivot table)
        heatmap_data = df_with_cats.pivot_table(
            values='primary_metric_value',
            index='test_name',
            columns='os_version',
            aggfunc='mean'
        )
        
        # Calculate percent change for heatmap
        pct_change_data = pd.DataFrame(index=heatmap_data.index)
        for i in range(1, len(os_versions)):
            if os_versions[i-1] in heatmap_data.columns and os_versions[i] in heatmap_data.columns:
                col_name = f"{os_versions[i-1]}→{os_versions[i]}"
                pct_change_data[col_name] = (
                    (heatmap_data[os_versions[i]] - heatmap_data[os_versions[i-1]]) / 
                    heatmap_data[os_versions[i-1]] * 100
                )
        
        # Generate summary
        num_regressions = len(regressions)
        if num_regressions > 0:
            top_regressions = regressions.head(3)
            summary_lines = [f"{num_regressions} regression(s) detected"]
            for _, row in top_regressions.iterrows():
                summary_lines.append(
                    f"• {row['test_name']}: {row['percent_change']:.1f}% in {row['current_version']} vs {row['baseline_version']}"
                )
            summary = '\n'.join(summary_lines)
        else:
            summary = "No significant regressions detected"
        
        return {
            'regressions': regressions.to_dict('records') if not regressions.empty else [],
            'summary': summary,
            'heatmap_data': pct_change_data,
            'comparison_data': comparison_df,
            'num_regressions': num_regressions
        }
    
    def analyze_peer_os_comparison(
        self,
        df: pd.DataFrame,
        baseline_os: str = 'RHEL',
        peer_os_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare RHEL performance against peer operating systems.
        
        Args:
            df: Input DataFrame
            baseline_os: OS to use as baseline (default: RHEL)
            peer_os_list: List of peer OS vendors to compare, or None for auto-detect
            
        Returns:
            Dictionary with peer comparison results
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Auto-detect OS vendors if not provided
        if not peer_os_list:
            all_os = df_with_cats['os_vendor'].dropna().unique()
            peer_os_list = [os for os in all_os if os != baseline_os]
        
        if len(peer_os_list) == 0:
            return {
                'comparison_data': pd.DataFrame(),
                'summary': 'No peer operating systems found for comparison',
                'competitive_count': 0,
                'total_benchmarks': 0
            }
        
        # Group by benchmark category and compare
        comparison_results = []
        
        for category in df_with_cats['benchmark_category'].unique():
            category_df = df_with_cats[df_with_cats['benchmark_category'] == category]
            
            for test in category_df['test_name'].unique():
                test_df = category_df[category_df['test_name'] == test]
                
                baseline_data = test_df[test_df['os_vendor'] == baseline_os]['primary_metric_value']
                
                if len(baseline_data) > 0:
                    baseline_mean = baseline_data.mean()
                    
                    for peer_os in peer_os_list:
                        peer_data = test_df[test_df['os_vendor'] == peer_os]['primary_metric_value']
                        
                        if len(peer_data) > 0:
                            peer_mean = peer_data.mean()
                            relative_perf = (peer_mean / baseline_mean) * 100 if baseline_mean > 0 else 100
                            
                            comparison_results.append({
                                'benchmark_category': category,
                                'test_name': test,
                                'baseline_os': baseline_os,
                                'peer_os': peer_os,
                                'baseline_value': baseline_mean,
                                'peer_value': peer_mean,
                                'relative_performance': relative_perf,
                                'is_competitive': relative_perf >= 90  # Within 10%
                            })
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # Generate summary
        if not comparison_df.empty:
            total_comparisons = len(comparison_df)
            competitive_count = comparison_df['is_competitive'].sum()
            
            # Find areas where peers are significantly better
            peer_advantages = comparison_df[comparison_df['relative_performance'] > 115].sort_values('relative_performance', ascending=False)
            
            summary_lines = [f"{baseline_os} competitive in {competitive_count}/{total_comparisons} benchmark comparisons"]
            
            if len(peer_advantages) > 0:
                for _, row in peer_advantages.head(3).iterrows():
                    advantage = row['relative_performance'] - 100
                    summary_lines.append(
                        f"⚠️ {row['peer_os']} {advantage:.0f}% faster in {row['test_name']}"
                    )
            
            summary = '\n'.join(summary_lines)
        else:
            summary = "Insufficient data for peer comparison"
            competitive_count = 0
            total_comparisons = 0
        
        return {
            'comparison_data': comparison_df,
            'summary': summary,
            'competitive_count': competitive_count,
            'total_benchmarks': total_comparisons
        }
    
    def analyze_cloud_scaling(
        self,
        df: pd.DataFrame,
        cloud_provider: str,
        os_version: str,
        instance_family: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze how performance scales across cloud instance sizes.
        
        Args:
            df: Input DataFrame
            cloud_provider: Cloud provider to analyze
            os_version: OS version to analyze
            instance_family: Instance family pattern to filter (e.g., 'c2-standard'), or None for all
            
        Returns:
            Dictionary with scaling analysis results
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Filter data
        filtered_df = df_with_cats[
            (df_with_cats['cloud_provider'] == cloud_provider) &
            (df_with_cats['os_version'] == os_version)
        ]
        
        if instance_family:
            filtered_df = filtered_df[filtered_df['instance_type'].str.contains(instance_family, na=False)]
        
        if filtered_df.empty:
            return {
                'scaling_data': pd.DataFrame(),
                'summary': 'No data available for selected configuration',
                'linear_scaling_count': 0,
                'total_benchmarks': 0
            }
        
        # Group by instance type and benchmark
        scaling_results = []
        
        instance_types = sorted(filtered_df['instance_type'].unique())
        
        for category in filtered_df['benchmark_category'].unique():
            category_df = filtered_df[filtered_df['benchmark_category'] == category]
            
            for test in category_df['test_name'].unique():
                test_df = category_df[category_df['test_name'] == test]
                
                for instance in instance_types:
                    instance_data = test_df[test_df['instance_type'] == instance]['primary_metric_value']
                    
                    if len(instance_data) > 0:
                        # Extract CPU cores if available
                        cores_data = test_df[test_df['instance_type'] == instance]['cpu_cores']
                        cores = cores_data.iloc[0] if len(cores_data) > 0 and not pd.isna(cores_data.iloc[0]) else None
                        
                        scaling_results.append({
                            'benchmark_category': category,
                            'test_name': test,
                            'instance_type': instance,
                            'cpu_cores': cores,
                            'mean_performance': instance_data.mean(),
                            'std_performance': instance_data.std()
                        })
        
        scaling_df = pd.DataFrame(scaling_results)
        
        # Analyze scaling efficiency
        summary_lines = []
        linear_scaling_count = 0
        total_benchmarks = len(scaling_df['test_name'].unique()) if not scaling_df.empty else 0
        
        if not scaling_df.empty and len(instance_types) >= 2:
            for test in scaling_df['test_name'].unique():
                test_data = scaling_df[scaling_df['test_name'] == test].sort_values('cpu_cores')
                
                if len(test_data) >= 2:
                    # Check if performance scales linearly with cores
                    first_perf = test_data.iloc[0]['mean_performance']
                    first_cores = test_data.iloc[0]['cpu_cores']
                    last_perf = test_data.iloc[-1]['mean_performance']
                    last_cores = test_data.iloc[-1]['cpu_cores']
                    
                    if first_cores and last_cores and first_cores > 0 and first_perf > 0:
                        expected_scaling = last_cores / first_cores
                        actual_scaling = last_perf / first_perf
                        scaling_efficiency = (actual_scaling / expected_scaling) * 100
                        
                        if scaling_efficiency >= 85:  # Within 15% of linear
                            linear_scaling_count += 1
                        elif scaling_efficiency < 70:  # Poor scaling
                            summary_lines.append(
                                f"⚠️ {test} shows diminishing returns (scaling efficiency: {scaling_efficiency:.0f}%)"
                            )
            
            summary = f"✅ Linear scaling observed for {linear_scaling_count}/{total_benchmarks} workloads\n" + '\n'.join(summary_lines)
        else:
            summary = "Insufficient data for scaling analysis"
        
        return {
            'scaling_data': scaling_df,
            'summary': summary,
            'linear_scaling_count': linear_scaling_count,
            'total_benchmarks': total_benchmarks
        }


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

