import math
import re
from datetime import datetime

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    if not isinstance(data.get("lamp_id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", data["lamp_id"]):
        raise ValueError("Invalid lamp_id")
    for field, limit in [("ambient_lux", 100000), ("simulation_hour", 24)]:
        value = data.get(field)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError("Invalid " + field)
    if data["simulation_hour"] >= 24:
        raise ValueError("Invalid simulation_hour")
    if type(data.get("motion")) is not bool:
        raise ValueError("Invalid motion")
    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    position = data.get("activity_position", 0)
    if type(position) is not int or not 0 <= position <= 5:
        raise ValueError("Invalid activity_position")
    if type(data.get("demo_mode", False)) is not bool:
        raise ValueError("Invalid demo_mode")
    return timestamp

