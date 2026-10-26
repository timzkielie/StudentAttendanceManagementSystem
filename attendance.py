"""Mark attendance: pick a class, pick a date, mark everyone, save.

If attendance was already saved for that class and date, it is loaded back in
and saving simply updates it (no more "already marked" dead end).
"""
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox

import database
from database import DatabaseManager
from assets.theme import COLORS, STATUS_COLORS, font
from assets.widgets import AppButton, ClassPicker, DatePicker, ScrollFrame, StatusToggle, page_header


db = DatabaseManager()  # always the same shared instance (Singleton)

BACKGROUND = COLORS["background"]
SURFACE = COLORS["surface"]


class AttendancePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BACKGROUND)
        self.app = app
        self.course = self.section = None
        self.toggles = {}
        self.names = {}
        self.dirty = False  # True when there are marks that were not saved yet
        self._loaded_date = date.today()

        self.header = page_header(
            self, "Mark attendance", "Choose a course and section to record attendance.", "attendance"
        )
        self.header.pack(fill="x", padx=28, pady=(22, 8))
        self.back_button = AppButton(self.header.actions, "‹  BACK TO CLASSES", self.back, "secondary")

        self.pick_view = tk.Frame(self, bg=BACKGROUND)
        self.picker = ClassPicker(
            self.pick_view,
            db.get_courses,
            db.get_sections,
            self.open_class,
            "Step 1: choose a course.",
        )
        self.picker.pack(fill="x", padx=28, pady=8)

        self.mark_view = tk.Frame(self, bg=BACKGROUND)
        self._build_mark_view()
        self._show(self.pick_view)

    # -- layout ------------------------------------------------------------
    def _build_mark_view(self):
        top = tk.Frame(self.mark_view, bg=SURFACE, padx=18, pady=12)
        top.pack(fill="x", padx=28, pady=(0, 10))
        left = tk.Frame(top, bg=SURFACE)
        left.pack(side="left")
        self.class_label = tk.Label(left, bg=SURFACE, fg=COLORS["text"], font=font(14, "bold"))
        self.class_label.pack(anchor="w")
        self.notice_label = tk.Label(left, bg=SURFACE, fg=COLORS["text_secondary"], font=font(9))
        self.notice_label.pack(anchor="w")

        picker_holder = tk.Frame(top, bg=SURFACE)
        picker_holder.pack(side="right")
        self.date_picker = DatePicker(picker_holder, on_change=self._on_date_change)
        self.date_picker.pack(side="right")
        tk.Label(picker_holder, text="DATE", bg=SURFACE, fg=COLORS["text_secondary"],
                 font=font(9, "bold")).pack(side="right", padx=(0, 10))

        bottom = tk.Frame(self.mark_view, bg=SURFACE, padx=18, pady=12)
        bottom.pack(side="bottom", fill="x", padx=28, pady=(10, 20))
        self.progress_label = tk.Label(bottom, bg=SURFACE, fg=COLORS["text_secondary"], font=font(10, "bold"))
        self.progress_label.pack(side="left")
        AppButton(bottom, "SAVE ATTENDANCE", self.save, large=True).pack(side="right")
        AppButton(bottom, "MARK ALL PRESENT", lambda: self.mark_all("PRESENT"), "success", large=True).pack(
            side="right", padx=(0, 10)
        )
        AppButton(bottom, "CLEAR", lambda: self.mark_all(None), "secondary", large=True).pack(
            side="right", padx=(0, 10)
        )

        self.rows = ScrollFrame(self.mark_view, BACKGROUND)
        self.rows.pack(fill="both", expand=True, padx=28)

    def _show(self, view):
        self.pick_view.pack_forget()
        self.mark_view.pack_forget()
        view.pack(fill="both", expand=True)
        in_marking = view is self.mark_view
        if in_marking:
            self.back_button.pack()
        else:
            self.back_button.pack_forget()
        self.header.subtitle_label.configure(
            text="Mark each student, then press SAVE ATTENDANCE."
            if in_marking else "Choose a course and section to record attendance."
        )

    # -- navigation --------------------------------------------------------
    def on_show(self):
        self.dirty = False
        self.picker.show_courses()
        self._show(self.pick_view)

    def back(self):
        if self.dirty and not messagebox.askyesno(
            "Unsaved attendance", "You have marks that are not saved yet. Leave without saving?", parent=self
        ):
            return
        self.dirty = False
        self.picker.reload()
        self._show(self.pick_view)

    def open_class(self, course, section):
        self.course, self.section = course, section
        self.class_label.configure(text=f"{course}  ·  Section {section}")
        students = db.get_students_in_class(course, section)
        self.names = {s["student_id"]: s["fullname"] for s in students}

        for widget in self.rows.inner.winfo_children():
            widget.destroy()
        self.toggles = {}
        for number, student in enumerate(students, start=1):
            row = tk.Frame(self.rows.inner, bg=SURFACE, padx=14, pady=8)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{number:02d}", width=4, bg=SURFACE, fg=COLORS["text_muted"],
                     font=font(10, "bold")).pack(side="left")
            info = tk.Frame(row, bg=SURFACE)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=student["fullname"], bg=SURFACE, fg=COLORS["text"],
                     font=font(11, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=student["student_id"], bg=SURFACE, fg=COLORS["text_secondary"],
                     font=font(9), anchor="w").pack(fill="x")
            toggle = StatusToggle(row, SURFACE, on_change=self._on_mark)
            toggle.pack(side="right")
            self.toggles[student["student_id"]] = toggle

        self.date_picker.set_date(date.today())
        self._load_saved(date.today())
        self.rows.scroll_to_top()
        self._show(self.mark_view)

    # -- marking -----------------------------------------------------------
    def _load_saved(self, day):
        """Fill the toggles with whatever was already saved for this class and date."""
        saved = db.get_class_attendance(self.course, self.section, day)
        for student_id, toggle in self.toggles.items():
            toggle.set(saved.get(student_id))
        self._loaded_date = day
        self.dirty = False
        self.notice_label.configure(
            text="Already recorded for this date. Saving will update it." if saved
            else "Not recorded yet for this date.",
            fg=STATUS_COLORS["LATE"]["solid"] if saved else COLORS["text_secondary"],
        )
        self._update_progress()

    def _on_date_change(self, day):
        if self.dirty and not messagebox.askyesno(
            "Unsaved attendance", "Load another date and discard the marks you just made?", parent=self
        ):
            self.date_picker.set_date(self._loaded_date)
            return
        self._load_saved(day)

    def _on_mark(self, _status):
        self.dirty = True
        self._update_progress()

    def mark_all(self, status):
        for toggle in self.toggles.values():
            toggle.set(status)
        self._on_mark(status)

    def _update_progress(self):
        values = [toggle.get() for toggle in self.toggles.values()]
        marked = sum(1 for value in values if value)
        parts = "     ".join(f"{status} {values.count(status)}" for status in database.STATUSES)
        self.progress_label.configure(
            text=f"{marked} of {len(values)} marked     |     {parts}",
            fg=STATUS_COLORS["PRESENT"]["solid"] if values and marked == len(values) else COLORS["text_secondary"],
        )

    def save(self):
        day = self.date_picker.get_date()
        if day is None:
            messagebox.showerror("Invalid date", "Type the date as YYYY-MM-DD, for example 2026-10-24.", parent=self)
            return
        if day > date.today():
            messagebox.showerror("Invalid date", "You cannot mark attendance for a future date.", parent=self)
            return
        missing = [self.names[sid] for sid, toggle in self.toggles.items() if not toggle.get()]
        if missing:
            shown = "\n".join(f"  •  {name}" for name in missing[:6])
            more = f"\n  …and {len(missing) - 6} more" if len(missing) > 6 else ""
            messagebox.showerror(
                "Incomplete attendance",
                f"Please choose PRESENT, LATE or ABSENT for every student.\n\nStill missing:\n{shown}{more}",
                parent=self,
            )
            return

        records = [(sid, toggle.get()) for sid, toggle in self.toggles.items()]
        db.save_attendance(records, day, datetime.now().time().replace(microsecond=0))
        self.dirty = False
        self.app.toast(f"Attendance saved for {self.course} · Section {self.section} ({day:%b %d, %Y})")
        # Stay on this list and reload what was just saved from the database,
        # so the statuses and the notice are refreshed.
        self._load_saved(day)
