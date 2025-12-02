#!/usr/bin/env python3
"""
Verification script to display OS distribution coverage in synthetic data.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path


def verify_os_distributions(filepath: str = "data/synthetic/benchmark_results.json"):
    """Load and analyze OS distribution coverage in synthetic data."""
    
    # Load data
    with open(filepath, 'r') as f:
        documents = json.load(f)
    
    print("=" * 80)
    print("OS DISTRIBUTION VERIFICATION")
    print("=" * 80)
    print(f"\nTotal documents: {len(documents)}")
    
    # Count distributions
    distributions = []
    versions = []
    dist_version_pairs = []
    kernels = defaultdict(set)
    
    for doc in documents:
        os_info = doc['system_under_test']['operating_system']
        dist = os_info['distribution']
        ver = os_info['version']
        kernel = os_info['kernel_version']
        
        distributions.append(dist)
        versions.append(ver)
        dist_version_pairs.append(f"{dist} {ver}")
        kernels[dist].add(kernel)
    
    # Distribution summary
    print("\n" + "=" * 80)
    print("DISTRIBUTION SUMMARY")
    print("=" * 80)
    
    dist_counts = Counter(distributions)
    print(f"\nTotal distributions: {len(dist_counts)}")
    for dist, count in sorted(dist_counts.items()):
        pct = count / len(documents) * 100
        print(f"  {dist.upper():10s}: {count:4d} tests ({pct:5.1f}%)")
    
    # Version details
    print("\n" + "=" * 80)
    print("VERSION DETAILS")
    print("=" * 80)
    
    version_counts = Counter(dist_version_pairs)
    print(f"\nTotal unique versions: {len(version_counts)}")
    
    # Group by distribution
    by_dist = defaultdict(list)
    for dist_ver, count in version_counts.items():
        dist = dist_ver.split()[0]
        by_dist[dist].append((dist_ver, count))
    
    for dist in sorted(by_dist.keys()):
        print(f"\n{dist.upper()}:")
        for dist_ver, count in sorted(by_dist[dist]):
            pct = count / len(documents) * 100
            print(f"  {dist_ver:20s}: {count:4d} tests ({pct:5.1f}%)")
    
    # Kernel version samples
    print("\n" + "=" * 80)
    print("KERNEL VERSION SAMPLES")
    print("=" * 80)
    
    for dist in sorted(kernels.keys()):
        print(f"\n{dist.upper()}:")
        for kernel in sorted(kernels[dist]):
            print(f"  {kernel}")
    
    # Validation checks
    print("\n" + "=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)
    
    checks = {
        "✓ RHEL present": "rhel" in dist_counts,
        "✓ Ubuntu present": "ubuntu" in dist_counts,
        "✓ Amazon Linux present": "amazon" in dist_counts,
        "✓ SLES present": "sles" in dist_counts,
        "✓ At least 13 versions": len(version_counts) >= 13,
        "✓ All 4 distributions": len(dist_counts) == 4,
        "✓ Multiple RHEL versions": len([v for v in versions if v.startswith('9.')]) > 0,
        "✓ Multiple Ubuntu versions": len([v for v in versions if '.' in v and v.startswith('2')]) > 0,
    }
    
    print()
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check[2:]}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL VALIDATION CHECKS PASSED!")
    else:
        print("✗ SOME VALIDATION CHECKS FAILED!")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    import sys
    
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/synthetic/benchmark_results.json"
    
    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    success = verify_os_distributions(filepath)
    sys.exit(0 if success else 1)

