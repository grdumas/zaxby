#!/usr/bin/env python3
"""
Minimal OpenSearch connectivity check using .env (same as the dashboard).

Run from project root:
  python check_opensearch_connection.py

Does not start the Dash app.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Load .env from this repo regardless of current working directory
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.opensearch_client import BenchmarkDataSource


def main() -> int:
    try:
        # __init__ verifies with client.info(); one extra info() gives a clean summary line.
        ds = BenchmarkDataSource()
        info = ds.client.info()
        print(
            f"OpenSearch OK — cluster {info['cluster_name']} "
            f"(OpenSearch {info['version']['number']})"
        )
        idx = ds.index_name or "(OPENSEARCH_INDEX not set)"
        print(f"  Index: {idx}")
        if ds.index_name and ds.client.indices.exists(index=ds.index_name):
            n = ds.client.count(index=ds.index_name)["count"]
            print(f"  Docs:    {n}")
        elif ds.index_name:
            print("  Warning: index does not exist on this cluster.")
        return 0
    except Exception as e:
        print(f"OpenSearch connection failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
