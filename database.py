"""Database layer: the ONLY file that talks to MySQL.

All SQL lives in the DatabaseManager class (a Singleton). Every other file
calls its methods, so SQL never leaks into the screens. Defaults match a fresh XAMPP install (user "root", empty password) and
can be overridden with ATTENDANCE_DB_HOST / _PORT / _NAME / _USER / _PASSWORD.
"""
import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import ClientFlag

DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "attendance_system"
DB_USER = "root"
DB_PASSWORD = ""

STATUSES = ("PRESENT", "LATE", "ABSENT")
_LEGACY_STATUSES = {"P": "PRESENT", "L": "LATE", "A": "ABSENT"}


class DatabaseConfigurationError(RuntimeError):
    pass


_COUNT_COLUMNS = """
    COALESCE(SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END), 0) AS present,
    COALESCE(SUM(CASE WHEN a.status = 'LATE' THEN 1 ELSE 0 END), 0) AS late,
    COALESCE(SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END), 0) AS absent
"""


class DatabaseManager:
    """The one and only gateway to MySQL (Singleton).

    DatabaseManager() always returns the SAME object, no matter how many
    times or from which file it is called, so the whole program shares one
    manager and one set of connection settings.
    """

    _instance = None
    STATUSES = STATUSES

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -----------------------------------------------------------------------
    # Connection helpers
    # -----------------------------------------------------------------------
    def _settings(self):
        try:
            port = int(os.environ.get("ATTENDANCE_DB_PORT", DB_PORT))
        except ValueError as error:
            raise DatabaseConfigurationError("ATTENDANCE_DB_PORT must be a number.") from error
        return {
            "host": os.environ.get("ATTENDANCE_DB_HOST", DB_HOST),
            "port": port,
            "user": os.environ.get("ATTENDANCE_DB_USER", DB_USER),
            "password": os.environ.get("ATTENDANCE_DB_PASSWORD", DB_PASSWORD),
            "connection_timeout": 10,
            "charset": "utf8mb4",
            # Make cursor.rowcount count rows that MATCHED, not only rows that
            # changed. Without it, saving an unchanged value looks like a failure.
            "client_flags": [ClientFlag.FOUND_ROWS],
        }


    def _database_name(self):
        return os.environ.get("ATTENDANCE_DB_NAME", DB_NAME)


    @contextmanager
    def open_cursor(self, commit=False):
        """Open a connection + cursor, and always close them again.

        with self.open_cursor(commit=True) as cur:   # commits on success, rolls back on error
            cur.execute("...", (value,))
        """
        connection = mysql.connector.connect(database=self._database_name(), **self._settings())
        cursor = connection.cursor(dictionary=True)
        try:
            yield cursor
            if commit:
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def _like(term):
        """Escape % and _ so users can search for them literally."""
        return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    @staticmethod
    def _as_text(value):
        return value.decode() if isinstance(value, (bytes, bytearray)) else str(value)


    # ---------------------------------------------------------------------------
    # Set-up and migrations (safe to run on every start)
    # ---------------------------------------------------------------------------
    def _ensure_database_exists(self):
        name = self._database_name().replace("`", "``")
        try:
            connection = mysql.connector.connect(**self._settings())
        except mysql.connector.Error:
            return  # self.init_db() will raise the real, readable error next
        try:
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4")
            connection.commit()
            cursor.close()
        except mysql.connector.Error:
            pass
        finally:
            connection.close()


    def init_db(self):
        self._ensure_database_exists()
        with self.open_cursor(commit=True) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(191) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id VARCHAR(191) NOT NULL PRIMARY KEY,
                    fullname VARCHAR(255) NOT NULL,
                    section VARCHAR(255) NOT NULL,
                    user_id INT NULL,
                    course VARCHAR(255) NOT NULL DEFAULT 'Unassigned'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("SHOW COLUMNS FROM students LIKE 'course'")
            if not cur.fetchall():
                cur.execute(
                    "ALTER TABLE students ADD COLUMN course VARCHAR(255) NOT NULL DEFAULT 'Unassigned'"
                )
            cur.execute("SHOW INDEX FROM students WHERE Key_name = 'idx_students_class'")
            if not cur.fetchall():  # fetchall: this index has 2 rows (course, section) and every row must be read
                cur.execute("CREATE INDEX idx_students_class ON students (course, section)")

            # ON UPDATE CASCADE lets a student ID be edited without breaking the
            # attendance rows; ON DELETE CASCADE removes a student's attendance too.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(191) NOT NULL,
                    status VARCHAR(10) NOT NULL,
                    attendance_date DATE NOT NULL,
                    attendance_time TIME NOT NULL,
                    UNIQUE KEY uq_attendance_student_date (student_id, attendance_date),
                    CONSTRAINT fk_attendance_student
                        FOREIGN KEY (student_id) REFERENCES students (student_id)
                        ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            self._migrate_status_column(cur)


    def _migrate_status_column(self, cur):
        """Old versions stored P / L / A in a CHAR(1). Convert to PRESENT / LATE / ABSENT."""
        cur.execute("SHOW COLUMNS FROM attendance LIKE 'status'")
        columns = cur.fetchall()
        column = columns[0] if columns else None
        if column and self._as_text(column["Type"]).lower().startswith("char(1)"):
            cur.execute("ALTER TABLE attendance MODIFY status VARCHAR(10) NOT NULL")
        for old, new in _LEGACY_STATUSES.items():
            cur.execute("UPDATE attendance SET status = %s WHERE status = %s", (new, old))


    # ---------------------------------------------------------------------------
    # Users
    # ---------------------------------------------------------------------------
    def get_user(self, username):
        with self.open_cursor() as cur:
            cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
            return cur.fetchone()


    def create_user(self, username, password_hash):
        """Return the new user id, or None if the username is taken."""
        try:
            with self.open_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password_hash),
                )
                return cur.lastrowid
        except mysql.connector.IntegrityError:
            return None


    def update_password_hash(self, user_id, password_hash):
        with self.open_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (password_hash, user_id))


    # ---------------------------------------------------------------------------
    # Students
    # ---------------------------------------------------------------------------
    def student_exists(self, student_id):
        with self.open_cursor() as cur:
            cur.execute("SELECT 1 FROM students WHERE student_id = %s", (student_id,))
            return cur.fetchone() is not None


    def add_student(self, student_id, fullname, course, section, created_by=None):
        try:
            with self.open_cursor(commit=True) as cur:
                cur.execute(
                    """INSERT INTO students (student_id, fullname, course, section, user_id)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (student_id, fullname, course, section, created_by),
                )
            return True
        except mysql.connector.IntegrityError:
            return False


    def update_student(self, old_id, new_id, fullname, course, section):
        """Return 'ok', 'duplicate' (new ID already used) or 'missing'."""
        try:
            with self.open_cursor(commit=True) as cur:
                cur.execute(
                    """UPDATE students
                       SET student_id = %s, fullname = %s, course = %s, section = %s
                       WHERE student_id = %s""",
                    (new_id, fullname, course, section, old_id),
                )
                return "ok" if cur.rowcount else "missing"
        except mysql.connector.IntegrityError:
            return "duplicate"


    def delete_student(self, student_id):
        """Delete a student and all of their attendance in one transaction."""
        with self.open_cursor(commit=True) as cur:
            cur.execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
            cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            return cur.rowcount > 0


    def get_student(self, student_id):
        with self.open_cursor() as cur:
            cur.execute(
                "SELECT student_id, fullname, course, section FROM students WHERE student_id = %s",
                (student_id,),
            )
            return cur.fetchone()


    def list_students(self, search="", course=None):
        """Students filtered by name/ID text and/or course."""
        conditions, parameters = [], []
        if search:
            conditions.append("(fullname LIKE %s OR student_id LIKE %s)")
            parameters += [self._like(search), self._like(search)]
        if course:
            conditions.append("course = %s")
            parameters.append(course)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        with self.open_cursor() as cur:
            cur.execute(
                f"""SELECT student_id, fullname, course, section FROM students {where}
                    ORDER BY course, section, fullname""",
                parameters,
            )
            return cur.fetchall()


    def get_courses(self):
        with self.open_cursor() as cur:
            cur.execute("""
                SELECT course, COUNT(*) AS total, COUNT(DISTINCT section) AS sections
                FROM students GROUP BY course ORDER BY course
            """)
            return cur.fetchall()


    def get_course_names(self):
        return [row["course"] for row in self.get_courses()]


    def get_sections(self, course):
        with self.open_cursor() as cur:
            cur.execute(
                """SELECT section, COUNT(*) AS total FROM students
                   WHERE course = %s GROUP BY section ORDER BY section""",
                (course,),
            )
            return cur.fetchall()


    def get_students_in_class(self, course, section):
        with self.open_cursor() as cur:
            cur.execute(
                """SELECT student_id, fullname FROM students
                   WHERE course = %s AND section = %s ORDER BY fullname""",
                (course, section),
            )
            return cur.fetchall()


    def get_overview(self):
        """Totals for the dashboard cards."""
        with self.open_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS students, COUNT(DISTINCT course) AS courses FROM students")
            totals = cur.fetchone()
            # A "section" only means something together with its course.
            cur.execute("SELECT COUNT(*) AS sections FROM (SELECT 1 FROM students GROUP BY course, section) AS c")
            totals["sections"] = cur.fetchone()["sections"]
        return totals


    # ---------------------------------------------------------------------------
    # Attendance
    # ---------------------------------------------------------------------------
    def get_class_attendance(self, course, section, att_date):
        """{student_id: status} already recorded for this class on this date."""
        with self.open_cursor() as cur:
            cur.execute(
                """SELECT a.student_id, a.status
                   FROM attendance a JOIN students s ON s.student_id = a.student_id
                   WHERE s.course = %s AND s.section = %s AND a.attendance_date = %s""",
                (course, section, att_date),
            )
            return {row["student_id"]: row["status"] for row in cur.fetchall()}


    def save_attendance(self, records, att_date, att_time):
        """Save [(student_id, status), ...] for one date. Existing marks are updated."""
        for _student_id, status in records:
            if status not in STATUSES:
                raise ValueError(f"Invalid attendance status: {status!r}")
        with self.open_cursor(commit=True) as cur:
            for student_id, status in records:
                cur.execute(
                    """INSERT INTO attendance (student_id, status, attendance_date, attendance_time)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           status = VALUES(status), attendance_time = VALUES(attendance_time)""",
                    (student_id, status, att_date, att_time),
                )


    def update_attendance_status(self, student_id, att_date, status):
        if status not in STATUSES:
            raise ValueError(f"Invalid attendance status: {status!r}")
        with self.open_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE attendance SET status = %s WHERE student_id = %s AND attendance_date = %s",
                (status, student_id, att_date),
            )
            return cur.rowcount > 0


    def get_attendance_counts(self, att_date):
        """{'PRESENT': n, 'LATE': n, 'ABSENT': n} for one day, school-wide."""
        counts = dict.fromkeys(STATUSES, 0)
        with self.open_cursor() as cur:
            cur.execute(
                "SELECT status, COUNT(*) AS total FROM attendance WHERE attendance_date = %s GROUP BY status",
                (att_date,),
            )
            for row in cur.fetchall():
                if row["status"] in counts:
                    counts[row["status"]] = row["total"]
        return counts

    @staticmethod
    def _as_ints(row):
        for key in ("present", "late", "absent"):
            row[key] = int(row[key])
        return row


    def get_class_summary(self, course, section):
        """One row per student with PRESENT / LATE / ABSENT totals."""
        with self.open_cursor() as cur:
            cur.execute(
                f"""SELECT s.student_id, s.fullname, {_COUNT_COLUMNS}
                    FROM students s LEFT JOIN attendance a ON a.student_id = s.student_id
                    WHERE s.course = %s AND s.section = %s
                    GROUP BY s.student_id, s.fullname ORDER BY s.fullname""",
                (course, section),
            )
            return [self._as_ints(row) for row in cur.fetchall()]


    def get_student_counts(self, student_id):
        with self.open_cursor() as cur:
            cur.execute(
                f"SELECT {_COUNT_COLUMNS} FROM attendance a WHERE a.student_id = %s",
                (student_id,),
            )
            return self._as_ints(cur.fetchone())


    def get_student_history(self, student_id):
        with self.open_cursor() as cur:
            cur.execute(
                """SELECT attendance_date, attendance_time, status FROM attendance
                   WHERE student_id = %s ORDER BY attendance_date DESC""",
                (student_id,),
            )
            return cur.fetchall()


    def get_attendance_by_date(self, att_date):
        with self.open_cursor() as cur:
            cur.execute(
                """SELECT s.student_id, s.fullname, s.course, s.section,
                          a.status, a.attendance_time
                   FROM attendance a JOIN students s ON s.student_id = a.student_id
                   WHERE a.attendance_date = %s ORDER BY s.course, s.section, s.fullname""",
                (att_date,),
            )
            return cur.fetchall()