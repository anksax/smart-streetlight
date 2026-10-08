"""Continuously publish five simulated lamps; settings remain dashboard-controlled."""
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

URL = os.environ["STREETLIGHT_URL"]
KEY = os.environ["STREETLIGHT_KEY"]
SETTINGS_URL = os.environ["DASHBOARD_URL"].rstrip("/") + "/api/settings"
INTERVAL = max(1.0, float(os.environ.get("SIMULATION_INTERVAL_SECONDS", "2")))


def send(reading):
    try:
        response = requests.post(
            URL, json=reading, headers={"x-functions-key": KEY}, timeout=(5, 10)
        )
        print("SENSOR:", json.dumps(reading), flush=True)
        print("CLOUD:", reading["lamp_id"], response.status_code, response.text, flush=True)
    except requests.RequestException as exc:
        print("Send failed:", reading["lamp_id"], type(exc).__name__, flush=True)


def validate(config):
    hour, lux = float(config["hour"]), float(config["lux"])
    position = config["activity_lamp"]
    if not 0 <= hour < 24 or not 0 <= lux <= 1000:
        raise ValueError("Invalid time or lux")
    if type(position) is not int or not 0 <= position <= 5:
        raise ValueError("Invalid activity position")
    if type(config["follow"]) is not bool:
        raise ValueError("Invalid follow setting")
    return hour, lux, position, config["follow"]


def main():
    with requests.Session() as session, ThreadPoolExecutor(max_workers=5) as pool:
        while True:
            started = time.monotonic()
            try:
                reply = session.get(SETTINGS_URL, timeout=(5, 10))
                reply.raise_for_status()
                hour, lux, position, follow = validate(reply.json())
            except (requests.RequestException, ValueError, KeyError, TypeError):
                print("Settings unavailable; retrying without publishing outdated inputs.", flush=True)
            else:
                readings = []
                for number in range(1, 6):
                    active = position != 0 and (
                        number == position or (follow and position < number <= position + 2)
                    )
                    readings.append(dict(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        lamp_id=f"L{number:02}",
                        simulation_hour=hour,
                        ambient_lux=round(max(0, lux + random.uniform(-2, 2)), 1),
                        motion=active,
                    ))
                # Await the complete batch: cycles never overlap.
                for _ in pool.map(send, readings):
                    pass
            time.sleep(max(0, INTERVAL - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Simulator stopped.", flush=True)
