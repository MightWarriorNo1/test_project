"""
Data simulator: physically consistent power flow with I²R technical losses and Is_Fraud labels.
Output: CSV/Parquet with V, I, P, timestamp (ISO 8601), meter_id, Is_Fraud.
Grid: 1 Transformer -> Junctions -> SmartMeters; DC power flow so KCL and Ohm hold.
"""

import argparse
import csv
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root for imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ntl_engine.simulator.grid import build_simple_feeder, solve_dc_power_flow, generate_timestep


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate grid telemetry with physics and fraud labels")
    parser.add_argument("--output", type=str, default="data/simulated", help="Output directory")
    parser.add_argument("--num-meters", type=int, default=20, help="Number of smart meters")
    parser.add_argument("--fraud-rate", type=float, default=0.1, help="Fraction of meters that are fraud")
    parser.add_argument("--num-steps", type=int, default=100, help="Number of timesteps")
    parser.add_argument("--format", choices=["csv", "parquet"], default="csv")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    G, meter_ids = build_simple_feeder(args.num_meters)
    n_fraud = max(1, int(args.num_meters * args.fraud_rate))
    fraud_meters = random.sample(meter_ids, n_fraud)

    start = datetime.now(timezone.utc)
    delta = timedelta(minutes=5)
    all_rows: List[dict] = []
    for step in range(args.num_steps):
        ts = start + step * delta
        all_rows.extend(generate_timestep(G, meter_ids, ts, fraud_meters=fraud_meters))

    if args.format == "csv":
        out_file = out_dir / "telemetry.csv"
        with open(out_file, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["meter_id", "V", "I", "P", "timestamp", "Is_Fraud"])
            w.writeheader()
            w.writerows(all_rows)
        print(f"Wrote {len(all_rows)} rows to {out_file}")
    else:
        try:
            import pandas as pd
            df = pd.DataFrame(all_rows)
            out_file = out_dir / "telemetry.parquet"
            df.to_parquet(out_file, index=False)
            print(f"Wrote {len(all_rows)} rows to {out_file}")
        except ImportError:
            print("Parquet requires pandas and pyarrow; writing CSV instead.")
            out_file = out_dir / "telemetry.csv"
            with open(out_file, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["meter_id", "V", "I", "P", "timestamp", "Is_Fraud"])
                w.writeheader()
                w.writerows(all_rows)
            print(f"Wrote {len(all_rows)} rows to {out_file}")


if __name__ == "__main__":
    main()
