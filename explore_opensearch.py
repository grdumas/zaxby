#!/usr/bin/env python3
"""
OpenSearch Schema Explorer

Run this script to:
1. Test OpenSearch connection
2. Explore available indices
3. Analyze schema structure
4. View sample documents

This will help document the actual data structure in docs/guides/SCHEMA.md
"""

import sys
from src.opensearch_client import main

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║    OpenSearch Schema Explorer                              ║
║    Performance Engineering Dashboard Project              ║
╚═══════════════════════════════════════════════════════════╝

This script will connect to OpenSearch and explore the schema.
Make sure you have configured .env with your OpenSearch credentials.

""")
    
    try:
        main()
        print("\n✓ Exploration complete!")
        print("\nNext steps:")
        print("  1. Review the output above")
        print("  2. Document findings in docs/guides/SCHEMA.md")
        print("  3. Generate synthetic data matching the schema")
    except KeyboardInterrupt:
        print("\n\nExploration cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Exploration failed: {e}")
        sys.exit(1)

