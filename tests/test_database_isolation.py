import sqlite3
import unittest
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

from database import DatabaseManager


class DictCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, parameters=()):
        query = query.replace(
            """ON DUPLICATE KEY UPDATE
                           status = VALUES(status), attendance_time = VALUES(attendance_time)""",
            """ON CONFLICT(student_id, attendance_date) DO UPDATE
                           SET status = excluded.status, attendance_time = excluded.attendance_time""",
        )
        self.cursor.execute(query.replace("%s", "?"), parameters)

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]

    @property
    def rowcount(self):
        return self.cursor.rowcount


class TestDatabaseUserIsolation(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL);
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                fullname TEXT NOT NULL,
                course TEXT NOT NULL,
                section TEXT NOT NULL,
                user_id INTEGER,
                email TEXT,
                mobile_number TEXT,
                age INTEGER,
                birth_date DATE,
                gender TEXT,
                year_level TEXT,
                modality TEXT,
                address TEXT,
                guardian_name TEXT,
                guardian_contact_number TEXT
            );
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                status TEXT NOT NULL,
                attendance_date DATE NOT NULL,
                attendance_time TEXT NOT NULL,
                UNIQUE (student_id, attendance_date),
                FOREIGN KEY (student_id) REFERENCES students(student_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            );
            INSERT INTO users VALUES (1, 'user_a'), (2, 'user_b');
            INSERT INTO students
                (student_id, fullname, course, section, user_id)
                VALUES ('A-1', 'Alice Student', 'BSIT', 'A', 1);
            INSERT INTO attendance (student_id, status, attendance_date, attendance_time)
                VALUES ('A-1', 'PRESENT', '2026-10-31', '08:00:00');
        """)
        self.db = DatabaseManager()
        self.open_cursor_patch = patch.object(self.db, "open_cursor", self.open_cursor)
        self.open_cursor_patch.start()
        self.addCleanup(self.open_cursor_patch.stop)
        self.addCleanup(self.connection.close)

    @contextmanager
    def open_cursor(self, commit=False):
        cursor = DictCursor(self.connection.cursor())
        try:
            yield cursor
            if commit:
                self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def test_new_user_has_empty_workspace_results(self):
        user_id = 2
        self.assertEqual(self.db.list_students("", None, user_id), [])
        self.assertEqual(self.db.get_courses(user_id), [])
        self.assertEqual(
            self.db.get_overview(user_id),
            {"students": 0, "courses": 0, "sections": 0},
        )
        day = date(2026, 10, 31).isoformat()
        self.assertEqual(self.db.get_attendance_by_date(day, user_id), [])
        self.assertEqual(self.db.get_attendance_counts(day, user_id), {
            "PRESENT": 0, "LATE": 0, "ABSENT": 0,
        })
        self.assertEqual(self.db.get_class_attendance("BSIT", "A", day, user_id), {})
        self.assertEqual(self.db.get_student_history("A-1", user_id), [])
        self.assertEqual(
            self.db.get_student_counts("A-1", user_id),
            {"present": 0, "late": 0, "absent": 0},
        )

    def test_user_b_cannot_get_update_or_delete_user_as_student(self):
        self.assertIsNone(self.db.get_student("A-1", 2))
        self.assertEqual(self.db.update_student("A-1", "A-2", "Changed Name", "BSIT", "B", 2), "missing")
        self.assertFalse(self.db.delete_student("A-1", 2))
        self.assertFalse(self.db.update_attendance_status("A-1", "2026-10-31", "ABSENT", 2))

    def test_user_b_actions_leave_user_as_data_unchanged(self):
        self.db.update_student("A-1", "A-2", "Changed Name", "BSIT", "B", 2)
        self.db.delete_student("A-1", 2)
        self.db.update_attendance_status("A-1", "2026-10-31", "ABSENT", 2)
        self.db.save_attendance([("A-1", "ABSENT")], "2026-10-31", "09:00:00", 2)

        self.assertEqual(
            self.db.get_student("A-1", 1),
            {
                "student_id": "A-1",
                "fullname": "Alice Student",
                "course": "BSIT",
                "section": "A",
            },
        )
        self.assertEqual(
            self.db.list_students("", None, 1),
            [{
                "student_id": "A-1",
                "fullname": "Alice Student",
                "course": "BSIT",
                "section": "A",
            }],
        )
        self.assertEqual(
            self.db.get_attendance_by_date("2026-10-31", 1)[0]["status"],
            "PRESENT",
        )
        self.assertEqual(
            self.db.get_student_counts("A-1", 1),
            {"present": 1, "late": 0, "absent": 0},
        )

    def test_bulk_import_is_owner_scoped_and_skips_duplicate_ids(self):
        record = {
            "student_id": "B-1",
            "fullname": "Zoë Student",
            "course": "BSIT",
            "section": "B",
            "email": "zoe@example.com",
            "mobile_number": None,
            "age": 20,
            "birth_date": None,
            "gender": None,
            "year_level": "2nd Year",
            "modality": None,
            "address": None,
            "guardian_name": None,
            "guardian_contact_number": None,
        }
        imported, duplicates = self.db.add_students_bulk([record, record], 2)

        self.assertEqual((imported, duplicates), (1, 1))
        self.assertEqual(
            self.db.get_student("B-1", 2),
            {
                "student_id": "B-1",
                "fullname": "Zoë Student",
                "course": "BSIT",
                "section": "B",
            },
        )
        self.assertIsNone(self.db.get_student("B-1", 1))
        saved = self.connection.execute(
            "SELECT email, age, user_id FROM students WHERE student_id = 'B-1'"
        ).fetchone()
        self.assertEqual(tuple(saved), ("zoe@example.com", 20, 2))


if __name__ == "__main__":
    unittest.main()
