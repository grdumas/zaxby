"""
Synthetic data generator for performance benchmarks.

Generates realistic benchmark data matching the OpenSearch schema structure
for development and testing purposes.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os


class SyntheticDataGenerator:
    """Generate synthetic benchmark results matching real OpenSearch schema."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional random seed."""
        random.seed(seed)
        
        # Configuration based on discovered schema
        self.os_versions = ["9.3", "9.4", "9.5", "9.6"]
        self.cloud_providers = ["aws", "azure", "gcp"]
        self.instance_types = {
            "aws": ["m5.24xlarge", "m5.12xlarge", "m5.8xlarge", "c5.24xlarge", "c5.12xlarge"],
            "azure": ["Standard_D96s_v3", "Standard_D48s_v3", "Standard_F96s_v2"],
            "gcp": ["n2-highmem-96", "n2-highmem-64", "c2-standard-60"]
        }
        self.test_types = [
            "coremark", "coremark_pro", "passmark", "streams", 
            "auto_hpl", "pyperf", "phoronix", "uperf", "pig"
        ]
        
        # Baseline metric values (will be varied)
        self.baseline_metrics = {
            "coremark": {"multicore_score": 500000.0, "singlecore_score": 5000.0},
            "coremark_pro": {"SUMM_CPU_mean": 55000.0, "SUMM_ME_mean": 2700.0},
            "passmark": {
                "CPU_INTEGER_MATH_mean": 270000.0,
                "CPU_FLOATINGPOINT_MATH_mean": 146000.0,
                "ME_WRITE_mean": 10000.0
            },
            "streams": {
                "copy__mb_per_sec": 180000.0,
                "scale__mb_per_sec": 140000.0,
                "add__mb_per_sec": 150000.0,
                "triad__mb_per_sec": 145000.0
            },
            "auto_hpl": {"gflops": 2500.0},
            "pyperf": {"mean": 0.5},
            "phoronix": {
                "hash_bops": 8000000.0,
                "pipe_bops": 17000000.0,
                "poll_bops": 5000000.0
            },
            "uperf": {
                "tcp_stream_bw_gbs": 9.5,
                "tcp_rr_trans_per_sec": 50000.0
            },
            "pig": {"throughput_mb_s": 150.0}
        }
        
    def generate_dataset(
        self,
        num_scenarios: int = 20,
        iterations_per_scenario: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete synthetic dataset.
        
        Args:
            num_scenarios: Number of unique configuration scenarios
            iterations_per_scenario: Test iterations per scenario
            
        Returns:
            List of synthetic benchmark documents
        """
        documents = []
        base_date = datetime.now() - timedelta(days=90)
        
        for i in range(num_scenarios):
            # Create a scenario configuration
            os_version = random.choice(self.os_versions)
            cloud_provider = random.choice(self.cloud_providers)
            instance_type = random.choice(self.instance_types[cloud_provider])
            test_type = random.choice(self.test_types)
            
            # Determine performance pattern for this scenario
            pattern = self._select_performance_pattern()
            
            # Generate iterations for this scenario
            for iteration in range(iterations_per_scenario):
                test_date = base_date + timedelta(
                    days=random.randint(0, 90),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                doc = self._generate_document(
                    os_version=os_version,
                    cloud_provider=cloud_provider,
                    instance_type=instance_type,
                    test_type=test_type,
                    test_date=test_date,
                    iteration=iteration,
                    pattern=pattern
                )
                documents.append(doc)
        
        return documents
    
    def _select_performance_pattern(self) -> Dict[str, Any]:
        """
        Select a performance pattern (regression, improvement, or stable).
        
        Returns:
            Dictionary with pattern type and magnitude
        """
        pattern_type = random.choices(
            ["stable", "improvement", "regression"],
            weights=[0.7, 0.15, 0.15]  # Most tests are stable
        )[0]
        
        if pattern_type == "stable":
            magnitude = random.uniform(0.95, 1.05)  # ±5%
        elif pattern_type == "improvement":
            magnitude = random.uniform(1.15, 1.30)  # 15-30% improvement
        else:  # regression
            magnitude = random.uniform(0.60, 0.80)  # 20-40% regression
        
        return {"type": pattern_type, "magnitude": magnitude}
    
    def _generate_document(
        self,
        os_version: str,
        cloud_provider: str,
        instance_type: str,
        test_type: str,
        test_date: datetime,
        iteration: int,
        pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single synthetic benchmark document."""
        
        doc_id = f"{test_type}_{random.randbytes(8).hex()}"
        scenario_name = f"rhel_{os_version.replace('.', '')}"
        
        doc = {
            "metadata": {
                "document_id": doc_id,
                "document_type": "zathras_test_result",
                "zathras_version": "1.0",
                "test_timestamp": test_date.isoformat() + "Z",
                "processing_timestamp": (test_date + timedelta(hours=6)).isoformat() + "Z",
                "collection_timestamp": test_date.isoformat() + "Z",
                "os_vendor": "rhel",
                "cloud_provider": cloud_provider,
                "instance_type": instance_type,
                "iteration": iteration,
                "scenario_name": scenario_name
            },
            "test": {
                "name": test_type,
                "version": "v1.22.zip",
                "wrapper_version": "v1.22.zip"
            },
            "system_under_test": self._generate_system_info(
                os_version, cloud_provider, instance_type
            ),
            "test_configuration": self._generate_test_config(
                cloud_provider, instance_type, test_type
            ),
            "runtime_info": {
                "command": "#/bin/bash",
                "user": "root"
            },
            "results": self._generate_results(test_type, pattern, iteration),
            "_export_metadata": {
                "exported_at": (test_date + timedelta(hours=6)).isoformat() + "Z",
                "exporter": "zathras-opensearch-exporter",
                "exporter_version": "1.0.0"
            }
        }
        
        return doc
    
    def _generate_system_info(
        self, os_version: str, cloud_provider: str, instance_type: str
    ) -> Dict[str, Any]:
        """Generate system_under_test object."""
        
        cpu_models = {
            "aws": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz",
            "azure": "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz",
            "gcp": "AMD EPYC 7B12 64-Core Processor"
        }
        
        # Vary CPU cores based on instance type
        cores = 96 if "96" in instance_type or "24xlarge" in instance_type else \
                64 if "64" in instance_type or "16xlarge" in instance_type else 48
        
        return {
            "hardware": {
                "cpu": {
                    "vendor": "GenuineIntel" if cloud_provider != "gcp" else "AuthenticAMD",
                    "model": cpu_models[cloud_provider],
                    "architecture": "x86_64",
                    "cores": cores,
                    "threads_per_core": 2,
                    "sockets": 2,
                    "numa_nodes": 2,
                    "cache_l3": "71.5 MiB (2 instances)"
                },
                "memory": {
                    "total_gb": 373 if cores >= 96 else 256,
                    "total_kb": 391500104 if cores >= 96 else 268435456,
                    "available_kb": 388185644 if cores >= 96 else 265000000
                },
                "storage": {
                    "device_0": {
                        "path": "10.7GB",
                        "type": "scsi"
                    }
                }
            },
            "operating_system": {
                "distribution": "rhel",
                "version": os_version,
                "kernel_version": f"5.14.0-503.11.1.el9_{os_version.split('.')[1]}.x86_64",
                "hostname": f"test-{cloud_provider}-{random.randint(100, 999)}.internal"
            },
            "configuration": {
                "tuned_profile": "virtual-guest",
                "sysctl_parameters": {
                    "kernel.numa_balancing": "1",
                    "net.core.somaxconn": "4096",
                    "vm.dirty_ratio": "30",
                    "vm.swappiness": "30"
                },
                "kernel_parameters": {
                    "console": ["tty0", "ttyS0,115200n8"],
                    "_total_parameters": 6
                }
            }
        }
    
    def _generate_test_config(
        self, cloud_provider: str, instance_type: str, test_type: str
    ) -> Dict[str, Any]:
        """Generate test_configuration object."""
        
        regions = {
            "aws": "us-east-2a",
            "azure": "eastus2",
            "gcp": "us-central1-a"
        }
        
        return {
            "iterations_requested": 1,
            "parameters": {
                "os_vendor": "rhel",
                "system_type": cloud_provider,
                "host_config": instance_type,
                "cloud_region": regions[cloud_provider],
                "test_to_run": [test_type],
                "test_iterations": 1,
                "User": "synthetic_user",
                "Owner": "perf_team",
                "Project": "Performance_Regression_Testing",
                "Environment": "Test"
            }
        }
    
    def _generate_results(
        self, test_type: str, pattern: Dict[str, Any], iteration: int
    ) -> Dict[str, Any]:
        """Generate results object with metrics."""
        
        # Get baseline metrics for this test type
        baseline = self.baseline_metrics.get(test_type, {})
        
        # Apply performance pattern and iteration variation
        magnitude = pattern["magnitude"]
        iteration_variance = random.uniform(0.98, 1.02)  # Small run-to-run variation
        
        metrics = {}
        for metric_name, baseline_value in baseline.items():
            # Apply pattern and variance
            value = baseline_value * magnitude * iteration_variance
            
            # For metrics with statistical aggregations (mean, min, max, stddev)
            if not metric_name.endswith(("_mean", "_min", "_max", "_stddev")):
                metrics[metric_name] = value
                metrics[f"{metric_name}_mean"] = value
                metrics[f"{metric_name}_min"] = value * 0.98
                metrics[f"{metric_name}_max"] = value * 1.02
                metrics[f"{metric_name}_stddev"] = value * 0.01
            else:
                metrics[metric_name] = value
        
        # Determine status based on pattern
        if pattern["type"] == "regression" and pattern["magnitude"] < 0.7:
            status = "FAIL"
        else:
            status = "PASS"
        
        # Select primary metric
        primary_metric_name = list(baseline.keys())[0] if baseline else "score"
        primary_metric_value = metrics.get(primary_metric_name, 0.0)
        
        return {
            "status": status,
            "total_runs": 1,
            "primary_metric": {
                "name": primary_metric_name,
                "value": primary_metric_value,
                "unit": self._get_metric_unit(test_type, primary_metric_name)
            },
            "runs": {
                "run_0": {
                    "run_number": 0,
                    "status": status,
                    "configuration": {
                        "test": test_type,
                        "results_version": "1.0"
                    },
                    "metrics": metrics
                }
            }
        }
    
    def _get_metric_unit(self, test_type: str, metric_name: str) -> str:
        """Get the appropriate unit for a metric."""
        
        if "gflops" in metric_name.lower():
            return "GFLOPS"
        elif "mb_per_sec" in metric_name.lower() or "mb_s" in metric_name.lower():
            return "MB/s"
        elif "bops" in metric_name.lower():
            return "BOPs"
        elif "gbs" in metric_name.lower():
            return "GB/s"
        elif "trans_per_sec" in metric_name.lower():
            return "transactions/sec"
        elif test_type == "pyperf":
            return "seconds"
        else:
            return "score"
    
    def save_to_file(self, documents: List[Dict[str, Any]], filename: str):
        """Save generated documents to a JSON file."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(documents, f, indent=2)
        print(f"Saved {len(documents)} documents to {filename}")


def main():
    """Generate synthetic dataset and save to files."""
    
    generator = SyntheticDataGenerator(seed=42)
    
    print("Generating synthetic benchmark data...")
    print("=" * 60)
    
    # Generate main dataset
    documents = generator.generate_dataset(
        num_scenarios=30,
        iterations_per_scenario=5
    )
    
    print(f"\nGenerated {len(documents)} documents")
    print(f"  Unique scenarios: 30")
    print(f"  Iterations per scenario: 5")
    
    # Save to file
    output_file = "data/synthetic/benchmark_results.json"
    generator.save_to_file(documents, output_file)
    
    # Generate summary statistics
    test_types = {}
    os_versions = {}
    cloud_providers = {}
    patterns = {"stable": 0, "improvement": 0, "regression": 0}
    
    for doc in documents:
        test_name = doc["test"]["name"]
        os_ver = doc["system_under_test"]["operating_system"]["version"]
        cloud = doc["metadata"]["cloud_provider"]
        status = doc["results"]["status"]
        
        test_types[test_name] = test_types.get(test_name, 0) + 1
        os_versions[os_ver] = os_versions.get(os_ver, 0) + 1
        cloud_providers[cloud] = cloud_providers.get(cloud, 0) + 1
        
        if status == "FAIL":
            patterns["regression"] += 1
        elif doc["results"]["primary_metric"]["value"] > 0:
            # Approximate pattern based on metric value variance
            patterns["stable"] += 1
    
    print("\n" + "=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"\nTest Types: {dict(test_types)}")
    print(f"\nOS Versions: {dict(os_versions)}")
    print(f"\nCloud Providers: {dict(cloud_providers)}")
    print(f"\nStatus Distribution:")
    print(f"  PASS: {sum(1 for d in documents if d['results']['status'] == 'PASS')}")
    print(f"  FAIL: {sum(1 for d in documents if d['results']['status'] == 'FAIL')}")
    
    print("\n✓ Synthetic data generation complete!")
    print(f"\nData saved to: {output_file}")


if __name__ == "__main__":
    main()

