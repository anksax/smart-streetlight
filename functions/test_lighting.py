import unittest
from datetime import datetime, timedelta, timezone
from lighting import decide


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, tzinfo=timezone.utc)

    def test_hysteresis(self):
        off = decide(600, 12, False, None, self.now)
        self.assertEqual(decide(299, 22, False, off, self.now)["state"], "OFF")
        dark = decide(279, 22, False, off, self.now)
        self.assertEqual(dark["state"], "DIM")
        self.assertEqual(decide(299, 22, False, dark, self.now)["state"], "DIM")
        self.assertEqual(decide(300, 22, False, dark, self.now)["state"], "OFF")

    def test_hold_expiry_and_refresh(self):
        on = decide(40, 22, True, None, self.now)
        held = decide(40, 22, False, on, self.now + timedelta(seconds=10))
        self.assertTrue(held["motion_held"])
        self.assertEqual(held["state"], "ON")
        self.assertEqual(decide(40, 22, False, on, self.now + timedelta(seconds=12))["state"], "DIM")
        renewed = decide(40, 22, True, on, self.now + timedelta(seconds=10))
        self.assertEqual(renewed["hold_remaining_seconds"], 12)

    def test_daylight_cancels_hold(self):
        on = decide(40, 22, True, None, self.now)
        off = decide(600, 12, False, on, self.now + timedelta(seconds=1))
        self.assertEqual(off["state"], "OFF")
        self.assertEqual(decide(40, 22, False, off, self.now + timedelta(seconds=2))["state"], "DIM")

    def test_first_reading_and_dark_daytime(self):
        self.assertEqual(decide(299, 22, False, None, self.now)["state"], "DIM")
        self.assertEqual(decide(300, 22, True, None, self.now)["state"], "OFF")
        self.assertEqual(decide(40, 12, False, None, self.now)["brightness"], 50)


if __name__ == "__main__":
    unittest.main()
