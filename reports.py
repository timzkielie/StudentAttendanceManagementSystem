"""Attendance reports.

Three tabs:  BY CLASS (course > section > students)  |  BY DATE  |  FIND STUDENT.
Opening a student shows their full attendance history. Every table can be
exported to a CSV file that opens in Excel.
"""
import csv
import re
import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog, messagebox

import database
from database import DatabaseManager
from assets.theme import COLORS, STATUS_COLORS, font
from assets.widgets import (
    AppButton, ClassPicker, DataTable, DatePicker, StatusToggle, center_window, make_entry, page_header,
    stat_card,
)


db = DatabaseManager()  # always the same shared instance (Singleton)

BACKGROUND = COLORS["background"]
SURFACE = COLORS["surface"]
TABS = (("class", "BY CLASS"), ("date", "BY DATE"), ("find", "FIND STUDENT"))


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def attendance_rate(present, late, absent):
    """Share of recorded days the student attended (PRESENT and LATE both count)."""
    total = present + late + absent
    return f"{(present + late) / total:.0%}" if total else "—"


def format_time(value):
    """MySQL returns TIME as a timedelta; show it as 8:05 AM."""
    if isinstance(value, timedelta):
        hours, remainder = divmod(int(value.total_seconds()), 3600)
        return f"{(hours % 12) or 12}:{remainder // 60:02d} {'AM' if hours % 24 < 12 else 'PM'}"
    return str(value)


def safe_filename(*parts):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", "_".join(str(p) for p in parts)).strip("_") + ".csv"


def open_status_dialog(app, student_id, fullname, att_date, current, on_saved):
    """Small window to change one attendance mark to PRESENT, LATE or ABSENT."""
    window = tk.Toplevel(app)
    window.title("Change attendance status")
    window.transient(app)
    window.configure(bg=SURFACE)
    window.resizable(False, False)

    panel = tk.Frame(window, bg=SURFACE, padx=26, pady=22)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text="Change attendance status", bg=SURFACE, fg=COLORS["text"],
             font=font(15, "bold")).pack(anchor="w")
    tk.Label(panel, text=f"{fullname}  ({student_id})\nDate: {att_date}", bg=SURFACE,
             fg=COLORS["text_secondary"], font=font(10), justify="left").pack(anchor="w", pady=(6, 16))
    toggle = StatusToggle(panel, SURFACE)
    toggle.set(current)
    toggle.pack(anchor="w")

    def save():
        status = toggle.get()
        if status != current and not db.update_attendance_status(student_id, att_date, status):
            messagebox.showerror("Update failed", "That attendance record no longer exists.", parent=window)
            return
        window.destroy()
        if status != current:
            app.toast("Attendance status updated.")
        on_saved()

    buttons = tk.Frame(panel, bg=SURFACE)
    buttons.pack(anchor="e", pady=(22, 0))
    AppButton(buttons, "CANCEL", window.destroy, "secondary").pack(side="left", padx=(0, 8))
    AppButton(buttons, "SAVE CHANGES", save).pack(side="left")

    center_window(window, app, 440, 270)
    window.wait_visibility()
    window.grab_set()


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------
class ReportsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BACKGROUND)
        self.app = app
        self.tab = "class"
        self.report_date = date.today()
        self._stack = []        # views we can go BACK to
        self._current = None    # (view function, arguments)
        self._export = None     # function returning (filename, headers, rows)
        self._search_text = ""
        self._search_job = None

        header = page_header(self, "Attendance reports", "Browse attendance by class, by date, or by student.", "report")
        header.pack(fill="x", padx=28, pady=(22, 8))
        self.export_button = AppButton(header.actions, "EXPORT CSV", self.export_csv, "secondary")
        self.export_button.pack()

        tabs = tk.Frame(self, bg=BACKGROUND)
        tabs.pack(fill="x", padx=28, pady=(0, 10))
        self.tab_buttons = {}
        for key, label in TABS:
            button = tk.Button(tabs, text=label, command=lambda k=key: self.select_tab(k), relief="flat", bd=0,
                               cursor="hand2", font=font(10, "bold"), padx=22, pady=9)
            button.pack(side="left", padx=(0, 6))
            self.tab_buttons[key] = button

        self.body = tk.Frame(self, bg=BACKGROUND)
        self.body.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        self._set_export(None)

    # -- navigation ----------------------------------------------------------
    def on_show(self, tab="class", date=None):  # noqa: A002 - "date" matches the caller's keyword
        if date is not None:
            self.report_date = date
        self.select_tab(tab)

    def select_tab(self, tab):
        self.tab = tab
        for key, button in self.tab_buttons.items():
            active = key == tab
            button.configure(
                bg=COLORS["accent"] if active else COLORS["surface_tint"],
                fg="#ffffff" if active else COLORS["text"],
                activebackground=COLORS["accent_hover"] if active else COLORS["border_strong"],
                activeforeground="#ffffff" if active else COLORS["text"],
            )
        self._stack.clear()
        view = {"class": self.view_classes, "date": self.view_by_date, "find": self.view_find}[tab]
        self._render(view, ())

    def _render(self, view, args):
        for widget in self.body.winfo_children():
            widget.destroy()
        self._set_export(None)
        self._current = (view, args)
        view(*args)

    def navigate(self, view, *args):
        """Open a deeper view and remember the current one so BACK works."""
        self._stack.append(self._current)
        self._render(view, args)

    def back(self):
        if self._stack:
            view, args = self._stack.pop()
            self._render(view, args)

    def _refresh(self):
        self._render(*self._current)

    def _toolbar(self, title, subtitle="", back=False):
        """Title row at the top of a view. Returns the frame for right-hand buttons."""
        bar = tk.Frame(self.body, bg=BACKGROUND)
        bar.pack(fill="x", pady=(0, 10))
        if back:
            AppButton(bar, "‹  BACK", self.back, "secondary").pack(side="left", padx=(0, 14))
        text = tk.Frame(bar, bg=BACKGROUND)
        text.pack(side="left")
        tk.Label(text, text=title, bg=BACKGROUND, fg=COLORS["text"], font=font(15, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(text, text=subtitle, bg=BACKGROUND, fg=COLORS["text_secondary"], font=font(10)).pack(anchor="w")
        actions = tk.Frame(bar, bg=BACKGROUND)
        actions.pack(side="right")
        return actions

    # -- CSV export ----------------------------------------------------------
    def _set_export(self, provider):
        self._export = provider
        self.export_button.set_enabled(provider is not None)

    def export_csv(self):
        if not self._export:
            return
        filename, headers, rows = self._export()
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv", initialfile=filename, filetypes=[("CSV file", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:  # utf-8-sig: Excel reads it correctly
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        self.app.toast("Report exported.")

    # -- view: BY CLASS ------------------------------------------------------
    def view_classes(self):
        picker = ClassPicker(
            self.body,
            db.get_courses,
            db.get_sections,
            lambda course, section: self.navigate(self.view_class_report, course, section),
            "Choose a course to see its sections.",
        )
        picker.pack(fill="x")
        picker.show_courses()

    def view_class_report(self, course, section):
        summary = db.get_class_summary(course, section)
        actions = self._toolbar(f"{course}  ·  Section {section}", f"{len(summary)} student(s)", back=True)
        table = DataTable(
            self.body,
            [
                ("student_id", "Student ID", 130, "center"),
                ("fullname", "Full name", 300, "w"),
                ("present", "PRESENT", 100, "center"),
                ("late", "LATE", 100, "center"),
                ("absent", "ABSENT", 100, "center"),
                ("rate", "Attendance rate", 130, "center"),
            ],
            empty_text="No students in this section.",
        )
        table.pack(fill="both", expand=True)
        rows = [
            (r["student_id"], r["fullname"], r["present"], r["late"], r["absent"],
             attendance_rate(r["present"], r["late"], r["absent"]))
            for r in summary
        ]
        table.set_rows((row[0], row, None) for row in rows)
        table.on_open(lambda student_id: self.navigate(self.view_student, student_id))
        AppButton(actions, "OPEN RECORD", lambda: self._open_selected(table)).pack()
        self._set_export(lambda: (
            safe_filename("attendance", course, section),
            ["Student ID", "Full name", "PRESENT", "LATE", "ABSENT", "Attendance rate"],
            rows,
        ))

    def _open_selected(self, table):
        student_id = table.selected_iid()
        if student_id:
            self.navigate(self.view_student, student_id)
        else:
            messagebox.showinfo("Open record", "Select a student in the table first.", parent=self)

    # -- view: BY DATE -------------------------------------------------------
    def view_by_date(self):
        actions = self._toolbar("Attendance by date", "Everyone who was marked on the chosen day.")
        AppButton(actions, "CHANGE STATUS", self._change_selected_status, "secondary").pack(side="right")
        DatePicker(actions, self.report_date, self._load_date).pack(side="right", padx=(0, 12))

        self.date_summary = tk.Label(self.body, bg=BACKGROUND, fg=COLORS["text_secondary"], font=font(10, "bold"))
        self.date_summary.pack(anchor="w", pady=(0, 8))
        self.date_table = DataTable(
            self.body,
            [
                ("course", "Course", 130, "center"),
                ("section", "Section", 90, "center"),
                ("student_id", "Student ID", 130, "center"),
                ("fullname", "Full name", 280, "w"),
                ("status", "Status", 110, "center"),
                ("time", "Time", 110, "center"),
            ],
            empty_text="No attendance was recorded on this date.",
        )
        self.date_table.pack(fill="both", expand=True)
        self.date_table.on_open(lambda student_id: self.navigate(self.view_student, student_id))
        self._load_date(self.report_date)

    def _load_date(self, day):
        self.report_date = day
        records = db.get_attendance_by_date(day)
        self._date_records = {r["student_id"]: r for r in records}
        counts = {s: sum(1 for r in records if r["status"] == s) for s in database.STATUSES}
        self.date_summary.configure(
            text=f"{day:%A, %B %d, %Y}     |     " + "     ".join(f"{s} {n}" for s, n in counts.items())
        )
        rows = [
            (r["course"], r["section"], r["student_id"], r["fullname"], r["status"], format_time(r["attendance_time"]))
            for r in records
        ]
        self.date_table.set_rows((row[2], row, row[4]) for row in rows)
        self._set_export(lambda: (
            safe_filename("attendance", day.isoformat()),
            ["Course", "Section", "Student ID", "Full name", "Status", "Time"],
            rows,
        ))

    def _change_selected_status(self):
        student_id = self.date_table.selected_iid()
        if not student_id:
            messagebox.showinfo("Change status", "Select a student in the table first.", parent=self)
            return
        record = self._date_records[student_id]
        open_status_dialog(
            self.app, student_id, record["fullname"], self.report_date, record["status"],
            lambda: self._load_date(self.report_date),
        )

    # -- view: FIND STUDENT --------------------------------------------------
    def view_find(self):
        self._toolbar("Find a student", "Search by name or student ID, then open their record.")
        bar = tk.Frame(self.body, bg=BACKGROUND)
        bar.pack(fill="x", pady=(0, 10))
        self.find_entry = make_entry(bar, width=40)
        self.find_entry.pack(side="left", ipady=8)
        self.find_entry.insert(0, self._search_text)
        self.find_entry.bind("<KeyRelease>", self._search_soon)
        self.find_entry.bind("<Return>", lambda _e: self._run_search())
        AppButton(bar, "SEARCH", self._run_search).pack(side="left", padx=(10, 0))

        self.find_table = DataTable(
            self.body,
            [
                ("student_id", "Student ID", 130, "center"),
                ("fullname", "Full name", 300, "w"),
                ("course", "Course", 150, "center"),
                ("section", "Section", 90, "center"),
            ],
            empty_text="Type a name or student ID to search.",
        )
        self.find_table.pack(fill="both", expand=True)
        self.find_table.on_open(lambda student_id: self.navigate(self.view_student, student_id))
        self.find_entry.focus_set()
        if self._search_text:
            self._run_search()

    def _search_soon(self, _event=None):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self._run_search)

    def _run_search(self):
        self._search_text = self.find_entry.get().strip()
        if not self._search_text:
            self.find_table.set_empty_text("Type a name or student ID to search.")
            self.find_table.set_rows([])
            return
        students = db.list_students(self._search_text)
        self.find_table.set_empty_text("No students match your search.")
        self.find_table.set_rows(
            (s["student_id"], (s["student_id"], s["fullname"], s["course"], s["section"]), None) for s in students
        )

    # -- view: ONE STUDENT ---------------------------------------------------
    def view_student(self, student_id):
        student = db.get_student(student_id)
        if student is None:
            self.app.toast("That student no longer exists.", "error")
            self.back()
            return
        counts = db.get_student_counts(student_id)
        history = db.get_student_history(student_id)

        actions = self._toolbar(
            student["fullname"],
            f"{student['student_id']}  ·  {student['course']}  ·  Section {student['section']}",
            back=True,
        )
        AppButton(actions, "EDIT STUDENT", lambda: self.app.show_page("students", edit_id=student_id),
                  "secondary").pack(side="right")
        AppButton(actions, "CHANGE STATUS", lambda: self._change_history_status(student, table, rows_by_date)).pack(
            side="right", padx=(0, 8)
        )

        cards = tk.Frame(self.body, bg=BACKGROUND)
        cards.pack(fill="x", pady=(0, 10))
        definitions = [
            ("PRESENT", counts["present"], STATUS_COLORS["PRESENT"]["solid"]),
            ("LATE", counts["late"], STATUS_COLORS["LATE"]["solid"]),
            ("ABSENT", counts["absent"], STATUS_COLORS["ABSENT"]["solid"]),
            ("ATTENDANCE RATE", attendance_rate(counts["present"], counts["late"], counts["absent"]), COLORS["accent"]),
        ]
        for column, (label, value, color) in enumerate(definitions):
            cards.grid_columnconfigure(column, weight=1, uniform="student_cards")
            stat_card(cards, label, str(value), color=color).grid(
                row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0)
            )

        table = DataTable(
            self.body,
            [("date", "Date", 160, "center"), ("time", "Time", 160, "center"), ("status", "Status", 140, "center")],
            empty_text="No attendance has been recorded for this student yet.",
        )
        table.pack(fill="both", expand=True)
        rows_by_date = {str(h["attendance_date"]): h["status"] for h in history}
        rows = [(str(h["attendance_date"]), format_time(h["attendance_time"]), h["status"]) for h in history]
        table.set_rows((row[0], row, row[2]) for row in rows)
        self._set_export(lambda: (
            safe_filename("attendance", student["student_id"]), ["Date", "Time", "Status"], rows,
        ))

    def _change_history_status(self, student, table, rows_by_date):
        att_date = table.selected_iid()
        if not att_date:
            messagebox.showinfo("Change status", "Select a date in the table first.", parent=self)
            return
        open_status_dialog(
            self.app, student["student_id"], student["fullname"], att_date, rows_by_date[att_date], self._refresh
        )