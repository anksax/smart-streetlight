import unittest
from validation import validate


class ValidationTests(unittest.TestCase):
    def reading(self, **changes):
        data = dict(lamp_id="L01", timestamp="2026-10-08T18:00:00+00:00",
                    ambient_lux=40, simulation_hour=22, motion=False)
        return {**data, **changes}

    def test_valid_extremes(self):
        for lux in (0, 100000):
            for hour in (0, 23.99):
                validate(self.reading(ambient_lux=lux, simulation_hour=hour))

    def test_invalid_numeric_inputs(self):
        for field, values in {
            "ambient_lux": [-1, 100001, True, "40", None, float("nan"), float("inf")],
            "simulation_hour": [-1, 24, True, "22", None, float("nan")],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        validate(self.reading(**{field: value}))

    def test_invalid_types_and_identifiers(self):
        for changes in ({"motion": "false"}, {"lamp_id": "../bad"},
                        {"lamp_id": ""}, {"demo_mode": 1}, {"activity_position": True},
                        {"activity_position": 6}, {"timestamp": "2026-10-08T18:00:00"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    validate(self.reading(**changes))

    def test_missing_fields(self):
        for field in self.reading():
            data = self.reading()
            del data[field]
            with self.subTest(field=field):
                with self.assertRaises((ValueError, KeyError, AttributeError, TypeError)):
                    validate(data)


if __name__ == "__main__":
    unittest.main()
