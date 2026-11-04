# Student Attendance Management System

Desktop app (Python + Tkinter + MySQL) for managing students and recording daily
attendance as **PRESENT**, **LATE** or **ABSENT**.

## Run it (Windows + XAMPP)
1. Open the XAMPP Control Panel and **Start MySQL**.
2. Double-click `run_app.bat` (first launch installs the packages into `.venv`).
   Or from a terminal: `.venv\Scripts\python.exe main.py`
3. Click **Create an account**, sign in, and start by adding students.

The database `attendance_system` and all tables are created automatically.
XAMPP defaults are used (user `root`, empty password). To change them set
`ATTENDANCE_DB_HOST`, `ATTENDANCE_DB_PORT`, `ATTENDANCE_DB_NAME`,
`ATTENDANCE_DB_USER`, `ATTENDANCE_DB_PASSWORD`.

## Files
| File | Job |
|---|---|
| `main.py` | Window, sidebar, page switching, "saved!" messages, error handling |
| `database.py` | `DatabaseManager` (Singleton): all SQL, the only file that talks to MySQL, plus automatic upgrades |
| `auth.py` | Password hashing, sign-in/sign-up rules, Login and Register screens |
| `dashboard.py` | Totals, today's attendance, calendar |
| `add_students.py` | Student management: add, edit, search, delete, and preview/import student files |
| `student_import.py` | Flexible CSV/XLSX header detection and import validation |
| `attendance.py` | Mark attendance for a class and date |
| `reports.py` | Reports by class, by date, by student + CSV export |
| `assets/` | `theme.py` (colours), `widgets.py` (buttons, tables...), `illustrations.py` (artwork) |

## Upgrading an older database
On first start the app converts old `P / L / A` marks to `PRESENT / LATE / ABSENT`
adds a missing `course` column, indexes `students.user_id`, and assigns students
with a `NULL` owner to the oldest registered user. No data is lost.

## 1.4 User workspaces
Each user sees only the students they created. Their course and section lists,
attendance, dashboard totals, and reports are scoped to that same ownership.
Student IDs remain globally unique, and duplicate-ID messages do not reveal
which account owns an existing ID.

## Bulk student import
On the Students page, choose **UPLOAD STUDENT LIST** to select a CSV or Excel
(`.xlsx`) file. Column headings and order are detected automatically; double-click
a recognized field in the mapping list to change it or ignore an unused column.
Review all rows and validation messages before confirming. Student inserts run
in a database transaction. **EXCEL TEMPLATE** and **CSV TEMPLATE** save sample
files that can be used as starting points, but the templates are optional.

The app adds nullable columns for optional contact/profile information to the
existing `students` table on startup. It does not create another student table
or change attendance records. Install dependencies with
`python -m pip install -r requirements.txt` if they are not already available.

Account passwords must contain at least six ASCII letters or digits, with no
spaces or symbols. Passwords continue to be stored as salted PBKDF2 hashes.

## 2.6 Student ownership
`students.user_id` identifies the account that owns a student. The column is
indexed, and all student and attendance reads and changes are restricted to
that owner. Attendance is associated with its owner through the student record.

### Students data dictionary
| Column | Meaning |
|---|---|
| `student_id` | Globally unique student identifier |
| `fullname` | Student's full name |
| `course` | Course name |
| `section` | Section within the course |
| `user_id` | Owning account ID; indexed and used to enforce workspace isolation |

## 3.4 Data isolation per user
Every registered account has a separate workspace. Users can view or change
only their own students and the attendance records associated with those
students. Existing unowned records are migrated to the oldest account when the
application starts.

### Manual test cases
1. **Register new user -> Dashboard shows 0 students and Students list is empty.**
2. **User B cannot see User A's students.**
3. Register user 2 and confirm Dashboard, Students, Mark Attendance, and Reports
   are empty. Add a student as user 2, sign out, then sign back in as user 1 and
   confirm user 2's student is not visible.
