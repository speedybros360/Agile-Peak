"""
activity_streams.py

Usage:
    python activity_streams.py [year]

If no year is supplied, the script will look for
    activities_<current_year>.json

The output files are written in the same directory as this script.
"""

import json
import os
import sys
from datetime import datetime
import requests
from pathlib import Path

# ------------------------------------------------------------------
# 1. Configuration – put your Strava OAuth details here
# ------------------------------------------------------------------
STRAVA_CLIENT_ID = "YOUR_STRAVA_CLIENT_ID"
STRAVA_CLIENT_SECRET = "YOUR_STRAVA_CLIENT_SECRET"

# Token storage – you can also store this in a file if you wish
ACCESS_TOKEN = None  # set to None and the script will attempt to read token.json


def load_access_token() -> str:
    """Try to load an access token from a local file.  If not found, raise."""
    global ACCESS_TOKEN
    if ACCESS_TOKEN:
        return ACCESS_TOKEN

    token_file = Path("token.json")
    if not token_file.exists():
        raise RuntimeError(
            "No access token found.  Please authenticate with Strava and "
            "store the JSON in token.json."
        )
    with token_file.open() as f:
        data = json.load(f)
    ACCESS_TOKEN = data["access_token"]
    return ACCESS_TOKEN


# ------------------------------------------------------------------
# 2. Helper – load JSON from a file
# ------------------------------------------------------------------
def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


# ------------------------------------------------------------------
# 3. Find the most recent activity
# ------------------------------------------------------------------
def find_most_recent_activity(activities: list) -> dict:
    """Return the activity with the latest start_date."""
    return max(
        activities,
        key=lambda a: datetime.fromisoformat(a["start_date"].replace("Z", "+00:00")),
    )


# ------------------------------------------------------------------
# 4. Pull stream data from local testStreamData.json
# ------------------------------------------------------------------
def pull_local_stream(activity_id: int, stream_file: Path) -> dict:
    """Return the stream entry for a given activity id from local JSON."""
    streams = load_json(stream_file)
    # The file is a list of stream objects – find the one with matching id
    for entry in streams:
        if entry.get("id") == activity_id or str(entry.get("id")) == str(activity_id):
            return entry
    raise KeyError(f"Activity ID {activity_id} not found in local stream dump.")


# ------------------------------------------------------------------
# 5. Pull speed & elevation streams from Strava API
# ------------------------------------------------------------------
def pull_api_stream(activity_id: int, stream_types: list) -> dict:
    """
    Pull requested streams from Strava API.

    Returns a dictionary where keys are stream types and values
    are the corresponding data lists.
    """
    token = load_access_token()
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {
        "keys": ",".join(stream_types),
        "key_by_type": "true",
    }
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch streams for activity {activity_id}: "
            f"{resp.status_code} {resp.text}"
        )

    # The API returns a list of stream objects; convert to dict keyed by type
    streams = {stream["type"]: stream for stream in resp.json()}
    return streams


# ------------------------------------------------------------------
# 6. Main logic
# ------------------------------------------------------------------
def main(year: int = None):
    if year is None:
        year = datetime.now().year

    # Paths
    activities_file = Path(f"activities_{year}.json")
    local_streams_file = Path("json_dump/testStreamData.json")

    if not activities_file.exists():
        raise FileNotFoundError(f"{activities_file} does not exist.")
    if not local_streams_file.exists():
        raise FileNotFoundError(f"{local_streams_file} does not exist.")

    # Load activities
    activities = load_json(activities_file)

    if not isinstance(activities, list):
        raise ValueError("Activities file must contain a JSON array.")

    # Find most recent
    recent = find_most_recent_activity(activities)
    activity_id = recent["id"]
    print(f"Most recent activity: ID={activity_id}, name='{recent.get('name')}'")

    # Check for heart‑rate data
    has_hr = recent.get("has_heartrate", False)
    print(f"Has heart‑rate data: {has_hr}")

    if has_hr:
        # Pull local stream
        try:
            stream_data = pull_local_stream(activity_id, local_streams_file)
        except KeyError as e:
            print(e)
            return

        out_path = Path(f"{activity_id}_w_HR.json")
        with out_path.open("w") as f:
            json.dump(stream_data, f, indent=2)
        print(f"Saved HR stream to {out_path}")

    else:
        # Pull speed & elevation from API
        stream_types = ["speed", "elevation"]
        try:
            streams = pull_api_stream(activity_id, stream_types)
        except RuntimeError as e:
            print(e)
            return

        # Build the output structure
        out_obj = {
            activity_id: {
                "cadence": streams.get("cadence", {}).get("data"),
                "HR": streams.get("hr", {}).get("data") if "hr" in streams else None,
                "distance": streams.get("distance", {}).get("data"),
                "speed": streams.get("speed", {}).get("data"),
                "elevation": streams.get("elevation", {}).get("data"),
            }
        }

        out_path = Path(f"{activity_id}_noHR.json")
        with out_path.open("w") as f:
            json.dump(out_obj, f, indent=2)
        print(f"Saved non‑HR stream to {out_path}")


# ------------------------------------------------------------------
# 7. CLI entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Optional command‑line argument for year
    if len(sys.argv) > 2:
        print("Usage: python activity_streams.py [year]")
        sys.exit(1)

    requested_year = int(sys.argv[1]) if len(sys.argv) == 2 else None
    main(requested_year)