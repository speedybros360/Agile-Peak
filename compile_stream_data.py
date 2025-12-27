"""
activity_stream_fetcher.py

Fetches missing activity streams from Strava and stores them in a compilation file.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import requests


# --------------------------------------------------------------------------- #
# Configuration – edit if you want to change the file names
ACTIVITY_IDS_FILE = "activities_2025.json"

"""
current_year = datetime.now().strftime("%Y")
filename = f"compiled_{current_year}_stream_data.json"
"""
COMPILED_STREAMS_FILE = "Comprehensive_stream_data.json"

# --------------------------------------------------------------------------- #
# Helper functions
def load_json(file_path: str) -> dict:
    """Load JSON from a file; return an empty dict if the file does not exist."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        print(f"⚠️  Could not parse JSON in {file_path}: {exc}")
        sys.exit(1)


def save_json(data: dict, file_path: str) -> None:
    """Write a dictionary to a JSON file with pretty printing."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"✓  Saved updated compilation to {file_path}")


def get_missing_ids(all_ids: List[Union[int, Dict]], compiled_data: dict) -> List[int]:
    """Return a list of activity IDs that are not yet in the compiled data."""
    # Extract numeric ids from whatever the caller passes
    cleaned_ids = []
    for item in all_ids:
        if isinstance(item, int):
            cleaned_ids.append(item)
        elif isinstance(item, dict) and "id" in item:
            cleaned_ids.append(int(item["id"]))
        else:
            print(f"⚠️  Skipping unexpected item in all_ids: {item}")

    existing_ids = {
        int(key.split("_")[1]) for key in compiled_data.keys() if "_" in key
    }
    return [aid for aid in cleaned_ids if aid not in existing_ids]


def fetch_streams(activity_id: int, token: str) -> Dict:
    """Call the Strava API and return the stream data for a single activity."""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {
        "keys": ",".join(
            [
                "time",
                "distance",
                "altitude",
                "velocity_smooth",
                "heartrate",
                "cadence",
                "temp",
                "moving",
                "grade_smooth",
            ]
        ),
        "key_by_type": "true",
    }
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch streams for {activity_id}: "
            f"{resp.status_code} {resp.text}"
        )
    return resp.json()


def determine_activity_type(stream_data: dict,
                            activity_id: int,
                            metadata_lookup: dict) -> str:
    """
    Decide whether an activity is a run or a ride.

    Parameters
    ----------
    stream_data : dict
        The raw stream payload returned from Strava.
    activity_id : int
        The numeric id of the activity (e.g. 15204685612).
    metadata_lookup : dict
        A mapping {activity_id: activity_dict} built from activity_2025.json.

    Returns
    -------
    str
        One of 'run', 'ride' (or whatever you want to add later).
    """
    # 1️⃣ Try the explicit type fields from the metadata file
    meta = metadata_lookup.get(activity_id)
    if meta:
        # "type" is the primary indicator (e.g. "Run", "Ride")
        if "type" in meta and isinstance(meta["type"], str):
            t = meta["type"].lower()
            if t in {"run", "walk"}:
                return "run"
            if t == "ride":
                return "ride"

        # If "type" is missing, fall back to "sport_type"
        if "sport_type" in meta and isinstance(meta["sport_type"], str):
            t = meta["sport_type"].lower()
            if t in {"run", "walk"}:
                return "run"
            if t == "ride":
                return "ride"

    # 2️⃣ No explicit type – use the velocity heuristic (old behaviour)
    velocity = stream_data.get("velocity_smooth", {})
    max_speed = max(velocity.get("data", [])) if velocity else 0
    return "ride" if max_speed > 7 else "run"


# --------------------------------------------------------------------------- #
def main(token: str, activities_json_path: str | Path) -> None:
    # 1. Load activity IDs
    ids_data = load_json(activities_json_path)
    if not isinstance(ids_data, list):
        print(f"Expected a JSON array in {activities_json_path}")
        sys.exit(1)

    # 2. Load compiled streams
    compiled = load_json(COMPILED_STREAMS_FILE)

    # 3. Find missing IDs
    missing_ids = get_missing_ids(ids_data, compiled)
    if not missing_ids:
        print("✅ All activities are already in the compilation file.")
        return

    print(f"ℹ️  {len(missing_ids)} activities missing – fetching streams...")
   
   #4.1 Find activity types
    metadata_lookup = {
        int(act["id"]): act for act in load_json(ACTIVITY_IDS_FILE)
    }
    # 4. Fetch and store each missing activity
    for aid in missing_ids:
        try:
            stream = fetch_streams(aid, token)
            act_type = determine_activity_type(stream, aid, metadata_lookup)
            key_name = f"{act_type}_{aid}"
            compiled[key_name] = stream
        except Exception as exc:
            print(f"⚠️  Skipping {aid}: {exc}")
            continue

        act_type = determine_activity_type(stream, aid, metadata_lookup)
        key_name = f"{act_type}_{aid}"
        compiled[key_name] = stream
        print(f"✓  Stored {act_type} streams for activity {aid}")

    # 5. Save updated compilation file
    save_json(compiled, COMPILED_STREAMS_FILE)


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python activity_stream_fetcher.py <STRAVA_ACCESS_TOKEN>")
        sys.exit(1)

    access_token = sys.argv[1].strip()
    if not access_token:
        print("❌ You must provide a non‑empty Strava access token.")
        sys.exit(1)

    main(access_token)