"""Student management: add, edit, search and delete students on one screen.

The form on the left is used for BOTH adding and editing. Pressing EDIT (or
double-clicking a row) loads that student into the form; saving then updates
them instead of creating a new one.
"""
import re
import tkinter as tk
from tkinter import messagebox, ttk

from database import DatabaseManager
from assets.theme import COLORS, font
from assets.widgets import AppButton, DataTable, field_label, make_entry, page_header


db = DatabaseManager()  # always the same shared instance (Singleton)

BACKGROUND = COLORS["background"]
SURFACE = COLORS["surface"]
ALL_COURSES = "ALL COURSES"
ID_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9\-_./]*")

FIELDS = (
    ("student_id", "STUDENT ID", "Example: 2024-0001"),
    ("fullname", "FULL NAME", "Lastname, Firstname, Middlename"),
    ("course", "COURSE", "Choose from the list or type a new course"),
    ("section", "SECTION", "Choose from the list or type a new section"),
)


class StudentsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BACKGROUND)
        self.app = app
        self.editing_id = None
        self._search_job = None

        header = page_header(self, "Students", "Add, edit and look up student records.", "student")
        header.pack(fill="x", padx=28, pady=(22, 8))

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=28, pady=(4, 20))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self._build_form(body)
        self._build_table(body)

    # -- layout ------------------------------------------------------------
    def _build_form(self, body):
        form = tk.Frame(body, bg=SURFACE, padx=24, pady=22, width=370)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        form.pack_propagate(False)

        self.form_title = tk.Label(form, font=font(15, "bold"), bg=SURFACE, fg=COLORS["text"])
        self.form_title.pack(anchor="w")

        self.entries = {}
        for key, label, hint in FIELDS:
            field_label(form, label, SURFACE).pack(anchor="w", pady=(14, 3))
            if key in ("course", "section"):
                entry = ttk.Combobox(form, font=font(11))
            else:
                entry = make_entry(form)
                entry.bind("<Return>", lambda _e: self.save())
            entry.pack(fill="x", ipady=6)
            tk.Label(form, text=hint, font=font(8), bg=SURFACE, fg=COLORS["text_muted"]).pack(anchor="w", pady=(2, 0))
            self.entries[key] = entry

        # The section list depends on the course: refresh it when the course changes.
        course_box = self.entries["course"]
        course_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_sections())
        course_box.bind("<FocusOut>", lambda _e: self._refresh_sections())
        self.entries["section"].bind("<Return>", lambda _e: self.save())

        buttons = tk.Frame(form, bg=SURFACE)
        buttons.pack(fill="x", pady=(22, 0))
        self.save_button = AppButton(buttons, "SAVE STUDENT", self.save, large=True)
        self.save_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.clear_button = AppButton(buttons, "CLEAR", self.reset_form, "secondary", large=True)
        self.clear_button.pack(side="left")

    def _build_table(self, body):
        panel = tk.Frame(body, bg=BACKGROUND)
        panel.grid(row=0, column=1, sticky="nsew")

        toolbar = tk.Frame(panel, bg=BACKGROUND)
        toolbar.pack(fill="x", pady=(0, 10))
        self.search_entry = make_entry(toolbar, width=28)
        self.search_entry.pack(side="left", ipady=7)
        self.search_entry.bind("<KeyRelease>", self._search_soon)
        tk.Label(toolbar, text="Search by name or ID", font=font(9), bg=BACKGROUND,
                 fg=COLORS["text_muted"]).pack(side="left", padx=10)
        self.course_filter = ttk.Combobox(toolbar, state="readonly", width=22, font=font(10),
                                          values=[ALL_COURSES])
        self.course_filter.set(ALL_COURSES)
        self.course_filter.pack(side="right")
        self.course_filter.bind("<<ComboboxSelected>>", lambda _e: self.refresh_table())

        self.table = DataTable(
            panel,
            [
                ("student_id", "Student ID", 130, "center"),
                ("fullname", "Full name", 150, "center"),
                ("course", "Course", 150, "center"),
                ("section", "Section", 90, "center"),
            ],
            empty_text="No students found.",
        )
        self.table.pack(fill="both", expand=True)
        self.table.on_open(self.start_edit)

        footer = tk.Frame(panel, bg=BACKGROUND)
        footer.pack(fill="x", pady=(10, 0))
        self.count_label = tk.Label(footer, bg=BACKGROUND, fg=COLORS["text_secondary"], font=font(10))
        self.count_label.pack(side="left")
        AppButton(footer, "DELETE", self.delete_selected, "danger").pack(side="right")
        AppButton(footer, "EDIT", lambda: self.start_edit(self.table.selected_iid()), "secondary").pack(
            side="right", padx=(0, 8)
        )

    # -- showing the page --------------------------------------------------
    def on_show(self, edit_id=None):
        self._refresh_courses()
        self.refresh_table()
        if edit_id:
            self.start_edit(edit_id)
        else:
            self.reset_form()

    def _refresh_sections(self):
        """Fill the SECTION drop-down with the sections that already exist in the chosen course."""
        course = self.entries["course"].get().strip().upper()
        sections = [row["section"] for row in db.get_sections(course)] if course else []
        self.entries["section"]["values"] = sections

    def _refresh_courses(self):
        courses = db.get_course_names()
        self.entries["course"]["values"] = courses
        self.course_filter["values"] = [ALL_COURSES, *courses]
        if self.course_filter.get() not in (ALL_COURSES, *courses):
            self.course_filter.set(ALL_COURSES)

    def refresh_table(self):
        course = self.course_filter.get()
        students = db.list_students(
            self.search_entry.get().strip(), None if course == ALL_COURSES else course
        )
        self.table.set_rows(
            (s["student_id"], (s["student_id"], s["fullname"], s["course"], s["section"]), None)
            for s in students
        )
        self.count_label.configure(text=f"{len(students)} student(s)")

    def _search_soon(self, _event=None):
        """Wait 250 ms after the last key press so we don't query on every letter."""
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(250, self.refresh_table)

    # -- form --------------------------------------------------------------
    def _set(self, key, value):
        entry = self.entries[key]
        if isinstance(entry, ttk.Combobox):
            entry.set(value)
        else:
            entry.delete(0, "end")
            entry.insert(0, value)

    def reset_form(self, keep_class=False):
        """Back to 'Add' mode. keep_class=True keeps course + section for fast data entry."""
        self.editing_id = None
        for key in ("student_id", "fullname") + (() if keep_class else ("course", "section")):
            self._set(key, "")
        self._refresh_sections()
        self.form_title.configure(text="Add a student")
        self.save_button.configure(text="SAVE STUDENT")
        self.clear_button.configure(text="CLEAR")
        self.entries["student_id"].focus_set()

    def start_edit(self, student_id):
        if not student_id:
            messagebox.showinfo("Edit student", "Select a student in the table first.", parent=self)
            return
        student = db.get_student(student_id)
        if student is None:
            self.app.toast("That student no longer exists.", "error")
            self.refresh_table()
            return
        self.editing_id = student["student_id"]
        for key in self.entries:
            self._set(key, student[key])
        self._refresh_sections()
        self.form_title.configure(text="Edit student")
        self.save_button.configure(text="UPDATE STUDENT")
        self.clear_button.configure(text="CANCEL")
        self.entries["fullname"].focus_set()

    def _read_form(self):
        return {key: entry.get().strip().upper() for key, entry in self.entries.items()}

    @staticmethod
    def _problem_with(values):
        if not all(values.values()):
            return "Please fill in every field."
        if not ID_PATTERN.fullmatch(values["student_id"]):
            return "Student ID may only contain letters, numbers and the characters - _ . /"
        if len(values["fullname"]) < 3:
            return "Please enter the student's full name."
        return None

    def save(self):
        values = self._read_form()
        problem = self._problem_with(values)
        if problem:
            messagebox.showerror("Check the form", problem, parent=self)
            return
        if self.editing_id is None:
            self._add(values)
        else:
            self._update(values)

    def _add(self, values):
        if db.student_exists(values["student_id"]):
            messagebox.showerror("Duplicate ID", f"Student ID {values['student_id']} already exists.", parent=self)
            return
        created_by = self.app.session.user["id"] if self.app.session.user else None
        if not db.add_student(
            values["student_id"], values["fullname"], values["course"], values["section"], created_by
        ):
            messagebox.showerror("Could not save", "The student could not be saved.", parent=self)
            return
        self.app.toast(f"Student added: {values['fullname']}")
        self._refresh_courses()
        self.refresh_table()
        self.reset_form(keep_class=True)

    def _update(self, values):
        result = db.update_student(
            self.editing_id, values["student_id"], values["fullname"], values["course"], values["section"]
        )
        if result == "duplicate":
            messagebox.showerror("Duplicate ID", f"Student ID {values['student_id']} already exists.", parent=self)
            return
        if result == "missing":
            messagebox.showerror("Not found", "This student was deleted by someone else.", parent=self)
            self.reset_form()
            self.refresh_table()
            return
        self.app.toast("Student updated.")
        self._refresh_courses()
        self.refresh_table()
        self.reset_form()

    def delete_selected(self):
        student_id = self.table.selected_iid()
        if not student_id:
            messagebox.showinfo("Delete student", "Select a student in the table first.", parent=self)
            return
        student = db.get_student(student_id)
        if student is None:
            self.refresh_table()
            return
        if not messagebox.askyesno(
            "Delete student permanently",
            f"Delete {student['fullname']} ({student_id}) and ALL of their attendance records?\n\n"
            "This cannot be undone.",
            icon="warning",
            parent=self,
        ):
            return
        db.delete_student(student_id)
        if self.editing_id == student_id:
            self.reset_form()
        self.app.toast("Student deleted.")
        self._refresh_courses()
        self.refresh_table()
