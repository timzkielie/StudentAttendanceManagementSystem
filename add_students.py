"""Student management: add, edit, search and delete students on one screen.

The form on the left is used for BOTH adding and editing. Pressing EDIT (or
double-clicking a row) loads that student into the form; saving then updates
them instead of creating a new one.
"""
import re
import csv
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk

import mysql.connector
from openpyxl import Workbook
from openpyxl.utils.exceptions import InvalidFileException

from database import DatabaseManager
from assets.theme import COLORS, font
from assets.widgets import AppButton, DataTable, field_label, make_entry, page_header
from student_import import (
    FIELD_LABELS,
    IGNORE_FIELD,
    StudentFileError,
    assess_rows,
    import_template_rows,
    read_student_file,
    suggested_mapping,
)


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

        AppButton(form, "UPLOAD STUDENT LIST", self.upload_student_list, "primary").pack(
            fill="x", pady=(14, 8)
        )
        template_buttons = tk.Frame(form, bg=SURFACE)
        template_buttons.pack(fill="x")
        AppButton(
            template_buttons, "EXCEL TEMPLATE", lambda: self.save_template("xlsx"), "secondary"
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        AppButton(
            template_buttons, "CSV TEMPLATE", lambda: self.save_template("csv"), "secondary"
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

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

    def reset_for_sign_out(self):
        if self._search_job:
            self.after_cancel(self._search_job)
            self._search_job = None
        self.search_entry.delete(0, "end")
        self.course_filter.set(ALL_COURSES)
        self.course_filter["values"] = [ALL_COURSES]
        self.table.set_rows([])
        self.count_label.configure(text="0 student(s)")
        self.editing_id = None
        for entry in self.entries.values():
            entry.set("") if isinstance(entry, ttk.Combobox) else entry.delete(0, "end")
        self.entries["course"]["values"] = []
        self.entries["section"]["values"] = []
        self.form_title.configure(text="Add a student")
        self.save_button.configure(text="SAVE STUDENT")
        self.clear_button.configure(text="CLEAR")

    def _user_id(self):
        return self.app.session.user["id"]

    def _refresh_sections(self):
        """Fill the SECTION drop-down with the sections that already exist in the chosen course."""
        course = self.entries["course"].get().strip().upper()
        sections = [row["section"] for row in db.get_sections(course, self._user_id())] if course else []
        self.entries["section"]["values"] = sections

    def _refresh_courses(self):
        courses = db.get_course_names(self._user_id())
        self.entries["course"]["values"] = courses
        self.course_filter["values"] = [ALL_COURSES, *courses]
        if self.course_filter.get() not in (ALL_COURSES, *courses):
            self.course_filter.set(ALL_COURSES)

    def refresh_table(self):
        course = self.course_filter.get()
        students = db.list_students(
            self.search_entry.get().strip(), None if course == ALL_COURSES else course, self._user_id()
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

    # -- bulk import -------------------------------------------------------
    def save_template(self, file_type):
        """Create a sample student list in the requested format."""
        extension = ".xlsx" if file_type == "xlsx" else ".csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save student list template",
            defaultextension=extension,
            filetypes=[("Excel workbook", "*.xlsx")] if file_type == "xlsx"
            else [("CSV file", "*.csv")],
            initialfile=f"student_list_template{extension}",
        )
        if not path:
            return
        headers, sample = import_template_rows()
        try:
            if file_type == "xlsx":
                workbook = Workbook()
                worksheet = workbook.active
                worksheet.title = "Students"
                worksheet.append(headers)
                worksheet.append(sample)
                workbook.save(path)
            else:
                with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(headers)
                    writer.writerow(sample)
        except (OSError, PermissionError) as error:
            messagebox.showerror("Template could not be saved", str(error), parent=self)
            return
        self.app.toast("Student list template saved.")

    def upload_student_list(self):
        """Select a file, detect its columns, and open the review-before-import dialog."""
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose a student list",
            filetypes=[
                ("Student lists", "*.xlsx *.csv"),
                ("Excel workbook", "*.xlsx"),
                ("CSV file", "*.csv"),
            ],
        )
        if not path:
            return
        try:
            headers, rows = read_student_file(path)
        except (
            StudentFileError, OSError, ValueError, zipfile.BadZipFile, InvalidFileException,
        ) as error:
            messagebox.showerror("Unable to read student list", str(error), parent=self)
            return
        self._show_import_preview(path, headers, rows)

    def _show_import_preview(self, path, headers, rows):
        window = tk.Toplevel(self)
        window.title("Upload Student List")
        window.configure(bg=BACKGROUND)
        window.geometry("1100x760")
        window.minsize(850, 580)
        window.transient(self.winfo_toplevel())
        window.grab_set()
        self._import_window = window
        self._import_headers = headers
        self._import_rows = rows
        self._import_mapping = suggested_mapping(headers)
        self._import_results = []

        content = tk.Frame(window, bg=BACKGROUND, padx=20, pady=16)
        content.pack(fill="both", expand=True)
        tk.Label(
            content, text="Review student list", font=font(18, "bold"),
            bg=BACKGROUND, fg=COLORS["text"],
        ).pack(anchor="w")
        tk.Label(
            content, text=f"Selected file: {path}", font=font(9),
            bg=BACKGROUND, fg=COLORS["text_secondary"], anchor="w",
        ).pack(fill="x", pady=(3, 10))
        tk.Label(
            content,
            text="Double-click a recognized field to change its mapping. Unneeded columns can be set to Ignore.",
            font=font(9), bg=BACKGROUND, fg=COLORS["text_muted"], anchor="w",
        ).pack(fill="x", pady=(0, 5))

        mapping_frame = tk.Frame(content, bg=BACKGROUND)
        mapping_frame.pack(fill="x")
        self.mapping_table = ttk.Treeview(
            mapping_frame, columns=("uploaded", "recognized"), show="headings",
            height=min(6, max(2, len(headers))),
        )
        self.mapping_table.heading("uploaded", text="Uploaded File Column")
        self.mapping_table.heading("recognized", text="Recognized Student Information Field")
        self.mapping_table.column("uploaded", width=360, anchor="w")
        self.mapping_table.column("recognized", width=360, anchor="w")
        mapping_scroll = ttk.Scrollbar(
            mapping_frame, orient="vertical", command=self.mapping_table.yview
        )
        self.mapping_table.configure(yscrollcommand=mapping_scroll.set)
        self.mapping_table.pack(side="left", fill="x", expand=True)
        mapping_scroll.pack(side="right", fill="y")
        self._mapping_items = {}
        self._populate_mapping_table()
        self.mapping_table.bind("<Double-1>", self._edit_column_mapping)

        self.import_summary = tk.Label(
            content, text="", font=font(9, "bold"), bg=BACKGROUND,
            fg=COLORS["text_secondary"], justify="left", anchor="w",
        )
        self.import_summary.pack(fill="x", pady=(10, 8))

        preview_frame = tk.Frame(content, bg=BACKGROUND)
        preview_frame.pack(fill="both", expand=True)
        preview_columns = [f"file_{index}" for index in range(len(headers))]
        self.preview_columns = preview_columns
        self.preview_table = ttk.Treeview(
            preview_frame,
            columns=(*preview_columns, "status", "details"),
            show="headings",
        )
        for column, header in zip(preview_columns, headers):
            self.preview_table.heading(column, text=header)
            self.preview_table.column(column, width=125, minwidth=85, stretch=False)
        self.preview_table.heading("status", text="Import Status")
        self.preview_table.column("status", width=180, minwidth=155, stretch=False)
        self.preview_table.heading("details", text="Validation Details")
        self.preview_table.column("details", width=330, minwidth=220, stretch=True)
        vertical_scroll = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview_table.yview
        )
        horizontal_scroll = ttk.Scrollbar(
            preview_frame, orient="horizontal", command=self.preview_table.xview
        )
        self.preview_table.configure(
            yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set
        )
        self.preview_table.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        buttons = tk.Frame(content, bg=BACKGROUND)
        buttons.pack(fill="x", pady=(12, 0))
        self.confirm_import_button = AppButton(
            buttons, "CONFIRM IMPORT", self.confirm_student_import, "success"
        )
        self.confirm_import_button.pack(side="right")
        AppButton(
            buttons, "CANCEL", window.destroy, "secondary"
        ).pack(side="right", padx=(0, 8))
        self._refresh_import_preview()

    def _populate_mapping_table(self):
        for item in self.mapping_table.get_children():
            self.mapping_table.delete(item)
        self._mapping_items.clear()
        for index, header in enumerate(self._import_headers):
            item = f"column-{index}"
            field = self._import_mapping[header]
            label = FIELD_LABELS.get(field, IGNORE_FIELD)
            self.mapping_table.insert("", "end", iid=item, values=(header, label))
            self._mapping_items[item] = header

    def _edit_column_mapping(self, event):
        region = self.mapping_table.identify("region", event.x, event.y)
        column = self.mapping_table.identify_column(event.x)
        item = self.mapping_table.identify_row(event.y)
        if region != "cell" or column != "#2" or not item:
            return
        bounds = self.mapping_table.bbox(item, column)
        if not bounds:
            return
        if getattr(self, "_mapping_editor", None):
            self._mapping_editor.destroy()
        header = self._mapping_items[item]
        current = self._import_mapping[header]
        choices = [*FIELD_LABELS.values(), IGNORE_FIELD]
        editor = ttk.Combobox(self.mapping_table, values=choices, state="readonly")
        editor.set(FIELD_LABELS.get(current, IGNORE_FIELD))
        editor.place(x=bounds[0], y=bounds[1], width=bounds[2], height=bounds[3])
        self._mapping_editor = editor

        def finish(_event=None):
            selected = editor.get()
            reverse_labels = {label: field for field, label in FIELD_LABELS.items()}
            self._import_mapping[header] = reverse_labels.get(selected, IGNORE_FIELD)
            editor.destroy()
            self._mapping_editor = None
            self._populate_mapping_table()
            self._refresh_import_preview()

        def cancel(_event=None):
            editor.destroy()
            self._mapping_editor = None

        editor.bind("<<ComboboxSelected>>", finish)
        editor.bind("<Escape>", cancel)
        editor.focus_set()

    def _refresh_import_preview(self):
        mapped_id_headers = [
            header for header, field in self._import_mapping.items() if field == "student_id"
        ]
        student_ids = [
            str(row.get(mapped_id_headers[0], "")).strip()
            for row in self._import_rows
            if mapped_id_headers and str(row.get(mapped_id_headers[0], "")).strip()
        ]
        existing_ids = db.get_existing_student_ids(student_ids)
        self._import_results = assess_rows(
            self._import_rows, self._import_mapping, existing_ids
        )
        for item in self.preview_table.get_children():
            self.preview_table.delete(item)

        counts = {"VALID": 0, "DUPLICATE": 0, "INVALID": 0}
        for result in self._import_results:
            counts[result["status"]] += 1
            values = [result["raw"].get(header, "") for header in self._import_headers]
            status = {
                "VALID": "VALID - Ready to Import",
                "DUPLICATE": "DUPLICATE - Student ID already exists",
                "INVALID": "INVALID - Missing or incorrect information",
            }[result["status"]]
            self.preview_table.insert(
                "", "end",
                values=(*values, status, "; ".join(result["errors"])),
            )

        recognized = [
            header for header, field in self._import_mapping.items() if field != IGNORE_FIELD
        ]
        unrecognized = [
            header for header, field in self._import_mapping.items() if field == IGNORE_FIELD
        ]
        unrecognized_text = ", ".join(unrecognized) if unrecognized else "None"
        self.import_summary.configure(
            text=(
                f"Total Records Found: {len(self._import_results)}    "
                f"Valid Records: {counts['VALID']}    "
                f"Duplicate Records: {counts['DUPLICATE']}    "
                f"Invalid Records: {counts['INVALID']}\n"
                f"Detected Columns: {len(recognized)}    "
                f"Unrecognized Columns: {unrecognized_text}"
            )
        )
        self.confirm_import_button.set_enabled(counts["VALID"] > 0)

    def confirm_student_import(self):
        records = [
            result["values"] for result in self._import_results
            if result["status"] == "VALID"
        ]
        if not records:
            messagebox.showinfo(
                "Nothing to import", "There are no valid student records to import.",
                parent=self._import_window,
            )
            return
        try:
            imported, newly_duplicated = db.add_students_bulk(records, self._user_id())
        except mysql.connector.Error as error:
            messagebox.showerror(
                "Import failed", f"No student records were saved.\n\n{error}",
                parent=self._import_window,
            )
            return

        duplicate_count = sum(
            result["status"] == "DUPLICATE" for result in self._import_results
        ) + newly_duplicated
        invalid_count = sum(
            result["status"] == "INVALID" for result in self._import_results
        )
        self._refresh_courses()
        self.refresh_table()
        messagebox.showinfo(
            "Student Import Completed!",
            "Student Import Completed!\n\n"
            f"Successfully Imported: {imported}\n"
            f"Skipped Duplicates: {duplicate_count}\n"
            f"Invalid Records: {invalid_count}",
            parent=self._import_window,
        )
        self._import_window.destroy()

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
        student = db.get_student(student_id, self._user_id())
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
        user_id = self._user_id()
        if db.student_exists(values["student_id"], user_id):
            messagebox.showerror("Duplicate ID", "Student ID already exists.", parent=self)
            return
        if not db.add_student(
            values["student_id"], values["fullname"], values["course"], values["section"], user_id
        ):
            messagebox.showerror("Duplicate ID", "Student ID already exists.", parent=self)
            return
        self.app.toast(f"Student added: {values['fullname']}")
        self._refresh_courses()
        self.refresh_table()
        self.reset_form(keep_class=True)

    def _update(self, values):
        result = db.update_student(
            self.editing_id, values["student_id"], values["fullname"], values["course"], values["section"],
            self._user_id(),
        )
        if result == "duplicate":
            messagebox.showerror("Duplicate ID", "Student ID already exists.", parent=self)
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
        user_id = self._user_id()
        student = db.get_student(student_id, user_id)
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
        db.delete_student(student_id, user_id)
        if self.editing_id == student_id:
            self.reset_form()
        self.app.toast("Student deleted.")
        self._refresh_courses()
        self.refresh_table()