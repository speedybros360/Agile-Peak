"""
flexible_activity_id_lists.py
Create two lists of activity IDs:
  • runs_with_hr   : Run activities that report heart‑rate data
  • rides_with_hr  : Ride activities that report heart‑rate data
Usage:
    python flexible_activity_id_lists.py --input path/to/activities.json
"""

import json
import argparse
from pathlib import Path

def load_activities(path: Path):
    """Load activity JSON array from the given file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def filter_ids(activities):
    """Return two lists: runs and rides that have heart‑rate data."""
    runs, rides = [], []
    for act in activities:
        if act.get("type") not in {"Run", "Ride"} or not act.get("has_heartrate"):
            continue
        if act["type"] == "Run":
            runs.append(act["id"])
        else:  # Ride
            rides.append(act["id"])
    return runs, rides

def write_output(runs, rides, out_path: Path):
    """Write the two lists to a JSON file."""
    data = {"runs_with_hr": runs, "rides_with_hr": rides}
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"Saved activity IDs to {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Collect Run/Ride IDs with heart‑rate data.")
    parser.add_argument("--input", "-i", required=True, type=Path,
                        help="Path to the JSON file containing activities.")
    parser.add_argument("--output", "-o", default=Path("activity_ids.json"),
                        type=Path, help="Output JSON file (default: activity_ids.json).")
    args = parser.parse_args()

    activities = load_activities(args.input)
    runs, rides = filter_ids(activities)
    write_output(runs, rides, args.output)

if __name__ == "__main__":
    main()