"""
activity_stream_collector.py

Collect Strava activity streams for a list of IDs that are not already
present in `activity_stream_compilation.json`.

Usage:
    python activity_stream_collector.py <token> <id1,id2,...>

The token is a Strava OAuth bearer token.
IDs can be supplied as a comma‑separated list or read from stdin.

The script will:
    • Load / create activity_stream_compilation.json
    • Skip IDs that are already stored
    • GET the stream data for new IDs
    • Append each result to the JSON file

Author: <your name>
Date: 2025‑12‑26
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict

import requests  # pip install requests


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

STREAM_ENDPOINT_TEMPLATE = (
    "https://www.strava.com/api/v3/activities/{id}/streams"
)
STREAM_KEYS = [
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
# The file where we store all collected streams
COMPILE_FILE = Path("activity_stream_compilation.json")


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #

def load_existing_ids() -> set:
    """
    Load the file and return a set of activity IDs that are already present.
    If the file does not exist, return an empty set.
    """
    if not COMPILE_FILE.exists():
        return set()

    with COMPILE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # Expecting a list of dicts; each dict should have an 'id' field.
            return {str(entry["id"]) for entry in data if "id" in entry}
        except json.JSONDecodeError:
            print(f"[WARN] {COMPILE_FILE} is not valid JSON. Starting fresh.")
            return set()


def save_stream(entry: Dict) -> None:
    """
    Append a single stream entry to the JSON file.
    The file is stored as a list of entries. We open it in read‑write mode,
    load the existing list, append, and write back.
    """
    # Load current data
    if COMPILE_FILE.exists():
        with COMPILE_FILE.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Corrupt JSON; starting new file.")
                data = []
    else:
        data = []

    # Append the new entry
    data.append(entry)

    # Write back
    with COMPILE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def fetch_stream(activity_id: str, token: str) -> Dict:
    """
    Make a GET request to the Strava stream endpoint and return the JSON.
    Raises requests.HTTPError on non‑200 responses.
    """
    url = STREAM_ENDPOINT_TEMPLATE.format(id=activity_id)
    params = {
        "keys": ",".join(STREAM_KEYS),
        "key_by_type": "true",
    }
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------- #
# Main logic
# --------------------------------------------------------------------------- #

def main(activity_ids: List[str], token: str) -> None:
    # Load existing IDs to avoid duplicates
    existing_ids = load_existing_ids()
    print(f"Loaded {len(existing_ids)} already‑stored activity IDs.")

    # Filter out duplicates
    new_ids = [aid for aid in activity_ids if aid not in existing_ids]
    print(f"{len(new_ids)} new IDs to process.")

    for idx, aid in enumerate(new_ids, start=1):
        print(f"[{idx}/{len(new_ids)}] Fetching streams for activity {aid}...")
        try:
            stream_data = fetch_stream(aid, token)
        except requests.HTTPError as e:
            print(f"❌ Error fetching activity {aid}: {e}")
            continue

        # Add the original ID so we can identify later
        stream_data["id"] = int(aid)

        # Persist the data
        save_stream(stream_data)
        print(f"✅ Stored streams for activity {aid}.")

    print("All done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect Strava activity streams."
    )
    parser.add_argument(
        "token",
        help="Strava OAuth bearer token (e.g. 'Bearer abc123...'). "
             "If you only have the raw token, prepend it with 'Bearer '.",
    )
    parser.add_argument(
        "ids",
        help="Comma‑separated list of activity IDs, or a file path with "
             "one ID per line (use '-' for stdin).",
    )
    args = parser.parse_args()

    # Resolve IDs
    if os.path.isfile(args.ids) or (args.ids == "-"):
        # Read from file or stdin
        if args.ids == "-":
            lines = sys.stdin.read().splitlines()
        else:
            with open(args.ids, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        activity_ids = [line.strip() for line in lines if line.strip()]
    else:
        # Assume comma‑separated list
        activity_ids = [id_.strip() for id_ in args.ids.split(",") if id_.strip()]

    if not activity_ids:
        print("No activity IDs provided. Exiting.")
        sys.exit(1)

    main(activity_ids, args.token)