import unittest
from datetime import timedelta

import reports


class TestAttendanceRate(unittest.TestCase):
    def test_all_attended_is_100_percent(self):
        self.assertEqual(reports.attendance_rate(8, 2, 0), "100%")

    def test_late_counts_as_attended(self):
        self.assertEqual(reports.attendance_rate(3, 0, 1), "75%")

    def test_no_records_gives_dash(self):
        self.assertEqual(reports.attendance_rate(0, 0, 0), "—")


class TestFormatTime(unittest.TestCase):
    def test_morning_time(self):
        self.assertEqual(reports.format_time(timedelta(hours=8, minutes=5)), "8:05 AM")

    def test_afternoon_time(self):
        self.assertEqual(reports.format_time(timedelta(hours=13, minutes=30)), "1:30 PM")

    def test_non_timedelta_returned_as_text(self):
        self.assertEqual(reports.format_time("08:05"), "08:05")


if __name__ == "__main__":
    unittest.main()