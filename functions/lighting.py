from datetime import datetime, timedelta, timezone


def decide(lux, hour, motion, previous, now):
    """300 lux switches OFF; below 280 switches back to lighting.

    On a lamp's first reading, use the original 300-lux threshold.
    Hold uses server time, never the client timestamp.
    """
    if previous is None:
        dark = lux < 300
    else:
        was_dark = previous.get("dark", previous.get("state") != "OFF")
        dark = lux < (300 if was_dark else 280)
    until = now
    if previous and previous.get("hold_until"):
        until = datetime.fromisoformat(previous["hold_until"])
    if not dark:
        until = now
    elif motion:
        until = now + timedelta(seconds=12)
    remaining = max(0, int((until - now).total_seconds()))
    held = dark and not motion and until > now
    if not dark:
        state, brightness, reason = "OFF", 0, "Sufficient ambient light"
    elif motion or held:
        state, brightness = "ON", 100
        reason = "Activity detected" if motion else "Motion hold timer"
    else:
        state, brightness = "DIM", 30 if hour >= 18 or hour < 6 else 50
        reason = "Nighttime without activity" if brightness == 30 else "Low ambient light during daytime"
    return dict(state=state, brightness=brightness, reason=reason, dark=dark,
                hold_until=until.isoformat(), motion_held=held,
                hold_remaining_seconds=remaining)
