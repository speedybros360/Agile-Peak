"""
wrapper3.py

A tiny wrapper that:
  1. Runs the OAuth flow from API_oauth_activityread.py
  2. Uses the returned access token to pull the current‑year activities
     with Activity_data_retrieve.fetch_activities()
  3. Saves the data to activities_<YYYY>.json
  4. Calls compile_stream_data.main() to fetch any missing streams
     and store them in Comprehensive_stream_data.json.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# ------------------------------------------------------------------
# 1 Import the two modules that live in the same directory
# ------------------------------------------------------------------
try:
    from API_oauth_activityread import (
        TOKEN_FILE,
        exchange_code_for_token,  # we only need the token‑writer
    )
except Exception as exc:
    raise ImportError(
        "Could not import the OAuth helper. "
        f"Make sure API_oauth_activityread.py is in the same directory."
    ) from exc

try:
    import Activity_data_retrieve as adr
except Exception as exc:
    raise ImportError(
        "Could not import Activity_data_retrieve.py. "
        f"Make sure it is in the same directory."
    ) from exc

# ------------------------------------------------------------------
# 2 Helper: read or trigger the OAuth flow
# ------------------------------------------------------------------
def get_valid_token() -> str:
    """
    Return a valid access token.
    If the stored token is expired or missing, start the OAuth flow.
    """
    # 2.1: If token file exists, try to read it
    if TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text())
            access_token = data["access_token"]
            expires_at   = data.get("expires_at", 0)
        except Exception:
            access_token, expires_at = None, 0
    else:
        access_token, expires_at = None, 0

    # 2.2: If token is missing or expired → run OAuth
    if not access_token or expires_at <= int(datetime.now(timezone.utc).timestamp()):
        print("[INFO] No valid token found – launching OAuth flow…")
        import API_oauth_activityread as oauther
        oauther.main()            # <-- this will block until the flow completes

        data = json.loads(TOKEN_FILE.read_text())
        access_token = data["access_token"]

    return access_token

# ------------------------------------------------------------------
# 3 Main routine – glue everything together
# ------------------------------------------------------------------
def main() -> None:
    token = get_valid_token()
    print("[INFO] Using access token:", token[:4], "...")

    # 3.1: Pull activities
    activities = adr.fetch_activities(token)

    # 3.2: Write out a JSON file, same naming scheme as the original script
    current_year = datetime.now(timezone.utc).year
    activities_file = Path(f"json_dump/activities_{current_year}.json")

    try:
        with activities_file.open("w", encoding="utf-8") as f:
            json.dump(activities, f, indent=2)
        print(f"[SUCCESS] Wrote {len(activities)} activities to {activities_file}")
    except OSError as exc:
        print(f"[ERROR] Could not write file: {exc}")

    # ------------------------------------------------------------------
    # 3.3: Call compile_stream_data to fetch any missing streams
    # ------------------------------------------------------------------
    try:
        import compile_stream_data as csd  # local module in the same folder
    except Exception as exc:
        print(f"[WARN] Could not import compile_stream_data: {exc}")
        return

    # Pass the same activities file that we just wrote.
    csd.main(token, str(activities_file))

# ------------------------------------------------------------------
if __name__ == "__main__":
    main()