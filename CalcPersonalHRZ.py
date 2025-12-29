"""
Docstring for CalcPersonalHRZ
Usage:
    python find_max_hr.py path/to/activities.json

The JSON file is expected to have the following minimal structure:

{
    "activity_id_1": {
        "heartrate": {
            "data": [ 80, 85, 90, ... ]
        },
        ...
    },
    "activity_id_2": {
        "heartrate": {
            "data": [ 75, 78, ... ]
        },
        ...
    },
    ...
}
"""

import json
import sys
from pathlib import Path

def load_json(file_path: Path):
    """Read a JSON file and return the parsed object."""
    try:
        with file_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        print(f"❌  File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"❌  Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

def find_global_max_hr(data):
    """
    Walk through the data structure and return a tuple:
        (max_value, activity_id_where_found)
    """
    max_hr = None
    max_activity = None

    for activity_id, activity in data.items():
        # Guard against missing keys / wrong structure
        hr_data = activity.get("heartrate", {}).get("data")
        if not isinstance(hr_data, list):
            continue  # skip activities that don't have a proper HR list

        if not hr_data:
            continue  # empty list – nothing to do

        local_max = max(hr_data)
        if (max_hr is None) or (local_max > max_hr):
            max_hr = local_max
            max_activity = activity_id

    return max_hr, max_activity

def main():
    if len(sys.argv) != 2:
        print("Usage: python find_max_hr.py path/to/activities.json", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    data = load_json(json_path)
    max_hr, activity_id = find_global_max_hr(data)

    if max_hr is None:
        print("No heart‑rate data found in the file.")
    else:
        print(f"🏃‍♂️  Highest recorded heart‑rate: {max_hr} bpm")
        print(f"   (found in activity id: {activity_id})")

if __name__ == "__main__":
    main()