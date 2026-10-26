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
| `add_students.py` | Student management: add, edit, search, delete |
| `attendance.py` | Mark attendance for a class and date |
| `reports.py` | Reports by class, by date, by student + CSV export |
| `assets/` | `theme.py` (colours), `widgets.py` (buttons, tables...), `illustrations.py` (artwork) |

## Upgrading an older database
On first start the app converts old `P / L / A` marks to `PRESENT / LATE / ABSENT`
and adds a missing `course` column. No data is lost.
