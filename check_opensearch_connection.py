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

# Fixed label width for aligned CLI output (value column lines up).
_LABEL_WIDTH = 26


def main() -> int:
    try:
        # __init__ verifies with client.info(); one extra info() gives a clean summary line.
        ds = BenchmarkDataSource()
        info = ds.client.info()
        print(
            f"OpenSearch OK — cluster {info['cluster_name']} "
            f"(OpenSearch {info['version']['number']})"
        )
        idx = ds.index_name or "(no results index — set OPENSEARCH_INDEX or OPENSEARCH_INDEX_RESULTS)"
        print(f"  {'Results index:':<{_LABEL_WIDTH}}{idx}")
        if ds.index_name and ds.client.indices.exists(index=ds.index_name):
            n = ds.client.count(index=ds.index_name)["count"]
            print(f"  {'Docs:':<{_LABEL_WIDTH}}{n}")
        elif ds.index_name:
            print("  Warning: results index does not exist on this cluster.")
        if ds.timeseries_index:
            print(f"  {'Timeseries index:':<{_LABEL_WIDTH}}{ds.timeseries_index}")
        return 0
    except Exception as e:
        print(f"OpenSearch connection failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
