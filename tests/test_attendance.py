import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import attendance
import database


def make_page(day, marks):
    """Build an AttendancePage WITHOUT opening a window.

    marks = {"2024-0001": "PRESENT", "2024-0002": None, ...}
    """
    page = attendance.AttendancePage.__new__(attendance.AttendancePage)
    page.course, page.section = "BSIT", "DIAMOND"
    page.names = {sid: f"Student {sid}" for sid in marks}
    page.toggles = {sid: MagicMock(get=MagicMock(return_value=status))
                    for sid, status in marks.items()}
    page.date_picker = MagicMock(get_date=MagicMock(return_value=day))
    page.app = MagicMock()
    page._load_saved = MagicMock()
    page.dirty = True
    return page


@patch("attendance.messagebox")
@patch("attendance.db")
class TestSaveAttendance(unittest.TestCase):
    def test_valid_attendance_is_saved(self, mock_db, mock_box):
        page = make_page(date.today(), {"A1": "PRESENT", "A2": "LATE", "A3": "ABSENT"})
        page.save()
        mock_db.save_attendance.assert_called_once()
        records = mock_db.save_attendance.call_args[0][0]
        self.assertEqual(records, [("A1", "PRESENT"), ("A2", "LATE"), ("A3", "ABSENT")])
        self.assertFalse(page.dirty)
        page.app.toast.assert_called_once()
        mock_box.showerror.assert_not_called()

    def test_future_date_is_rejected(self, mock_db, mock_box):
        page = make_page(date.today() + timedelta(days=1), {"A1": "PRESENT"})
        page.save()
        mock_box.showerror.assert_called_once()
        mock_db.save_attendance.assert_not_called()

    def test_invalid_date_is_rejected(self, mock_db, mock_box):
        page = make_page(None, {"A1": "PRESENT"})
        page.save()
        mock_box.showerror.assert_called_once()
        mock_db.save_attendance.assert_not_called()

    def test_unmarked_student_is_rejected(self, mock_db, mock_box):
        page = make_page(date.today(), {"A1": "PRESENT", "A2": None})
        page.save()
        mock_box.showerror.assert_called_once()
        self.assertIn("Student A2", mock_box.showerror.call_args[0][1])
        mock_db.save_attendance.assert_not_called()


class TestStatusValidation(unittest.TestCase):
    """The database layer also refuses a bad status (no MySQL needed)."""

    def test_save_attendance_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            database.DatabaseManager().save_attendance(
                [("A1", "EXCUSED")], date.today(), None
            )

    def test_update_status_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            database.DatabaseManager().update_attendance_status("A1", date.today(), "P")


if __name__ == "__main__":
    unittest.main()