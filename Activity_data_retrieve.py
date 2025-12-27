"""
strava_activities_to_file.py

Fetches the authenticated athlete's activities from Strava for the current year
and writes them to a JSON file.

Usage:
    # 1. Pass token on the command line
    python strava_activities_to_file.py --token <YOUR_STRAVA_TOKEN>

    # 2. Or set an environment variable and run without arguments
    export STRAVA_TOKEN=<YOUR_STRAVA_TOKEN>
    python strava_activities_to_file.py
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #

def current_epoch() -> int:
    """Return the current UTC epoch time (seconds)."""
    return int(datetime.now(timezone.utc).timestamp())

def start_of_current_year_epoch() -> int:
    """Return the epoch time for 00:00 UTC on Jan 1 of the current year."""
    now = datetime.now(timezone.utc)
    start_of_year = datetime(year=now.year, month=1, day=1, tzinfo=timezone.utc)
    return int(start_of_year.timestamp())

# --------------------------------------------------------------------------- #
# Main logic
# --------------------------------------------------------------------------- #

def fetch_activities(token: str) -> list:
    """
    Calls the Strava API to get activities for the authenticated athlete.

    Parameters
    ----------
    token : str
        A valid OAuth access token with the `activity:read` scope.

    Returns
    -------
    list
        Parsed JSON response from the API (list of activity objects).
    """
    url = "https://www.strava.com/api/v3/athlete/activities"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "before": current_epoch(),
        "after": start_of_current_year_epoch(),
        "page": 1,
        "per_page": 200,
    }

    response = requests.get(url, headers=headers, params=params)

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        print(f"[ERROR] API request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    return response.json()

# --------------------------------------------------------------------------- #
# CLI handling
# --------------------------------------------------------------------------- #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch current year Strava activities and write them to a JSON file."
    )
    parser.add_argument(
        "--token",
        help="Strava OAuth access token (overrides STRAVA_TOKEN env var)",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    token = args.token or os.getenv("STRAVA_TOKEN")

    if not token:
        print("[ERROR] No Strava token provided.  Use --token or set STRAVA_TOKEN.", file=sys.stderr)
        sys.exit(1)

    activities = fetch_activities(token)

    # Determine output file name: activities_<YYYY>.json
    current_year = datetime.now(timezone.utc).year
    output_file = f"activities_{current_year}.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2)
        print(f"[INFO] Successfully wrote {len(activities)} activities to '{output_file}'.")
    except OSError as exc:
        print(f"[ERROR] Could not write to file: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()