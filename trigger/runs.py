"""Fake Strava run payloads shared by scripts/send_run.py and the trigger Lambda."""

RUNS = {
    "easy": {
        "name": "Easy morning run",
        "activity_type": "Run",
        "run_type": "easy",
        "distance_km": 8.3,
        "moving_time_min": 48,
        "pace_str": "5:47",
        "elevation_gain_m": 42,
        "avg_hr": 138.0,
        "hr_zones": {"1": 5, "2": 78, "3": 15, "4": 2, "5": 0},
        "splits": ["5:51", "5:49", "5:45", "5:44", "5:48", "5:50", "5:47", "5:43"],
    },
    "long": {
        "name": "Sunday long run",
        "activity_type": "Run",
        "run_type": "long",
        "distance_km": 18.5,
        "moving_time_min": 112,
        "pace_str": "6:03",
        "elevation_gain_m": 145,
        "avg_hr": 148.0,
        "hr_zones": {"1": 2, "2": 55, "3": 35, "4": 8, "5": 0},
        "splits": ["6:10", "6:05", "6:02", "5:58", "6:00", "6:04", "6:08", "6:12",
                   "6:15", "6:10", "6:05", "6:02", "6:08", "6:14", "6:18", "6:20",
                   "6:22", "5:58"],
    },
    "tempo": {
        "name": "Tempo Tuesday",
        "activity_type": "Run",
        "run_type": "tempo",
        "distance_km": 6.2,
        "moving_time_min": 28,
        "pace_str": "4:31",
        "elevation_gain_m": 18,
        "avg_hr": 171.0,
        "hr_zones": {"1": 0, "2": 5, "3": 18, "4": 62, "5": 15},
        "splits": ["4:42", "4:35", "4:29", "4:28", "4:27", "4:26"],
    },
}

# Missing the 'activity' wrapper: simulates a malformed Strava webhook and
# makes the handler raise KeyError, which is the failure demo.
BAD = {"name": "Morning run", "distance_km": 8.3, "moving_time_min": 48}


def message_for(run_type: str) -> dict:
    if run_type == "bad":
        return BAD
    return {"activity": RUNS[run_type]}
