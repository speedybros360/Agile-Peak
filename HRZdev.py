"""
Reads `datacrunchtest.json`, classifies heart‑rate values into zones, and
computes the total time spent in each zone.

Author:  <your name>
Date:    2025‑12‑26
"""

import json
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Load the JSON file
# --------------------------------------------------------------------------- #

DATA_FILE = Path("json_dump/datacrunchtest.json")

if not DATA_FILE.exists():
    raise FileNotFoundError(f"Could not find {DATA_FILE}")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

time_series      = data["run_16844801853"]["time"]["data"]      # list of timestamps (seconds)
heartrate_series = data["run_16844801853"]["heartrate"]["data"]  # list of heart‑rate values

# Sanity check – the two series must be the same length
if len(time_series) != len(heartrate_series):
    raise ValueError("Time and heart‑rate series are not the same length")

# --------------------------------------------------------------------------- #
# 2. Define the “hard” zones
# --------------------------------------------------------------------------- #

# You can change these thresholds to whatever makes sense for your training plan.
# The example below defines three hard zones:
#   Zone 1: 150–159 bpm
#   Zone 2: 160–169 bpm
#   Zone 3: ≥170 bpm

ZONE_DEFINITIONS = {
    "Zone 1 (0-119 bpm)":     lambda hr: 0 <= hr <=119,
    "Zome 2 (120‑144 bpm)":   lambda hr: 120 <= hr <= 144,
    "Zone 3 (145‑165 bpm)":   lambda hr: 145 <= hr <= 165,
    "Zone 4 (166‑177 bpm)":   lambda hr: 166 <= hr <= 177,
    "Zone 5 (≥178 bpm)":      lambda hr: hr >= 178
}

# --------------------------------------------------------------------------- #
# 3. Walk through the series and accumulate time per zone
# --------------------------------------------------------------------------- #

zone_time = {name: 0 for name in ZONE_DEFINITIONS}

# We assume that the `time` array is a simple monotonically increasing list of
# timestamps in seconds.  The time spent at each heart‑rate sample is the
# difference between successive timestamps.
for i in range(1, len(time_series)):
    dt = time_series[i] - time_series[i-1]   # elapsed seconds
    hr = heartrate_series[i]

    for zone_name, predicate in ZONE_DEFINITIONS.items():
        if predicate(hr):
            zone_time[zone_name] += dt
            break  # a heart‑rate can belong to only one zone

# --------------------------------------------------------------------------- #
# 4. Output the results
# --------------------------------------------------------------------------- #

print("\n=== Time spent in each hard zone ===")
total_time = sum(zone_time.values())
for name, seconds in (zone_time.items()):
    minutes, sec = divmod(seconds, 60)
    print(f"{name:25s}: {minutes} min {sec:02d} sec")

print("\nTotal hard‑zone time: "
      f"{total_time // 60} min {total_time % 60:02d} sec\n")