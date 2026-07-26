#!/usr/bin/env python3
"""Report latency metrics from JSONL log files.

Usage: python scripts/report_latency.py logs/session.jsonl
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def percentile(data: list[float], p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/report_latency.py <jsonl_file>")
        print("\nGenerates a latency report from structured log output.")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    metrics: dict[str, list[float]] = defaultdict(list)

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if "metric" in entry and "value_ms" in entry:
                    metrics[entry["metric"]].append(entry["value_ms"])
            except json.JSONDecodeError:
                continue

    if not metrics:
        print("No latency metrics found in file.")
        sys.exit(0)

    # Print report
    print(f"\n{'='*70}")
    print(f"LATENCY REPORT - {filepath.name}")
    print(f"{'='*70}")
    print(f"{'Metric':<30} {'Count':>6} {'P50':>8} {'P90':>8} {'P95':>8} {'Max':>8}")
    print("-" * 70)

    for name, values in sorted(metrics.items()):
        p50 = percentile(values, 50)
        p90 = percentile(values, 90)
        p95 = percentile(values, 95)
        mx = max(values)
        print(f"{name:<30} {len(values):>6} {p50:>7.1f}ms {p90:>7.1f}ms {p95:>7.1f}ms {mx:>7.1f}ms")

    print(f"{'='*70}")


if __name__ == "__main__":
    main()
