"""
find_hr_zones.py

Usage:
    python find_hr_zones.py <input_json> [<output_json>]

The script opens a JSON file that contains data from many activities.
For each activity the structure is:

    jsonfile[activity_id]["heartrate"]["data"]

`["heartrate"]["data"]` is a list of objects that each contain a key
`"value"` with the heart‑rate reading.

The script:

1. Finds the single highest heart‑rate value in **all** activities
   (the “HRMax”).
2. Computes the classic 5‑zone training zones that use percentages of
   HRMax:
        Zone 1 : 68-73.96% HRMax
        Zone 2 : 73.97–81.25%
        Zone 3 : 81.26–88.0%
        Zone 4 : 88.1–93.75%
        Zone 5 : > 93.76% HRMax
3. Prints the zone ranges to the console.
4. Stores the zones in a new JSON file with the following layout:

        {
            "Zone 1": { "min": 0,   "max": 50 },
            "Zone 2": { "min": 50,  "max": 60 },
            ...
        }

If you do not supply an output file name the script writes
`hr_zones.json` in the current working directory.
"""

import json
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

def load_json(path: Path):
    """Return the parsed JSON object from *path*."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def find_hrmax(data: dict) -> int | float:
    max_hr = None

    for act_id, activity in data.items():
        hr_section = activity.get("heartrate", {})
        readings = hr_section.get("data", [])

        for reading in readings:
            # Handle two common shapes:
            # 1. {"value": 145}
            # 2. 145
            if isinstance(reading, dict):
                hr_val = reading.get("value")
            else:
                hr_val = reading

            if hr_val is None:
                continue

            try:
                hr_val = float(hr_val)
            except (TypeError, ValueError):
                continue

            if max_hr is None or hr_val > max_hr:
                max_hr = hr_val

    if max_hr is None:
        raise ValueError("No heart‑rate data found in the file.")
    return max_hr


def compute_zones(hrmax: int | float) -> dict:
    """
    Compute the 5 training zones as percentages of HRMax.

    Parameters
    ----------
    hrmax : int | float
        The maximum heart‑rate value.

    Returns
    -------
    dict
        Mapping from zone name to a dict with keys "min" and "max".
    """
    # Classic percentages – you can tweak these if you prefer a different scheme
    zone_percents = [
        ("Zone 1", 0.682291666666667,   0.739583333333333),
        ("Zone 2", 0.7396,  0.8125),
        ("Zone 3", 0.8126,  0.880208333333333),
        ("Zone 4", 0.8803,  0.9375),
        ("Zone 5", 0.9376, 1),   # upper bound is inclusive
    ]

    zones = {}
    for name, low_pct, high_pct in zone_percents:
        min_val = round(hrmax * (low_pct), 1)
        max_val = round(hrmax * (high_pct), 1)
        zones[name] = {"min": min_val, "max": max_val}

    return zones


def write_json(path: Path, data):
    """Write *data* as pretty‑printed JSON to *path*."""
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4)
    print(f"\nZones written to {path.resolve()}")


# ------------------------------------------------------------------
# Main script logic
# ------------------------------------------------------------------

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(argv[0]).expanduser()
    if not input_path.is_file():
        print(f"❌  File does not exist: {input_path}")
        sys.exit(1)

    #   
    output_path = Path(argv[1]) if len(argv) > 1 else Path("json_dump/bad_call_hr_zones.json")


    # Load the data
    try:
        activities = load_json(input_path)
    except json.JSONDecodeError as e:
        print(f"❌  Failed to parse JSON: {e}")
        sys.exit(1)

    # Find HRMax
    try:
        hrmax = find_hrmax(activities)
    except ValueError as e:
        print(f"❌  {e}")
        sys.exit(1)

    print(f"\n🫀 HRMax found: {hrmax:.1f} bpm\n")

    # Compute zones
    zones = compute_zones(hrmax)

    # Pretty‑print to console
    print("Training Zones (bpm):")
    for zone, limits in zones.items():
        print(f"  {zone:6s} : {limits['min']:.1f} – {limits['max']:.1f}")

    # Save to JSON
    write_json(output_path, zones)


if __name__ == "__main__":
    main(sys.argv)