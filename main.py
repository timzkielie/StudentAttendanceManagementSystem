"""Student Attendance Management System - start here:  python main.py

main.py only builds the window, the sidebar and the navigation. Each screen
lives in its own file and is shown with app.show_page("name").
"""
import tkinter as tk
import traceback
from tkinter import messagebox

import mysql.connector

import auth
import database
from database import DatabaseManager
from add_students import StudentsPage
from assets.theme import COLORS, apply_ttk_theme, font
from assets.widgets import AppButton
from attendance import AttendancePage
from auth import LoginPage, RegisterPage
from dashboard import DashboardPage
from reports import ReportsPage


db = DatabaseManager()  # always the same shared instance (Singleton)

NAVIGATION = (
    ("dashboard", "Dashboard"),
    ("students", "Students"),
    ("attendance", "Mark Attendance"),
    ("reports", "Reports"),
)
PAGES = {
    "dashboard": DashboardPage,
    "students": StudentsPage,
    "attendance": AttendancePage,
    "reports": ReportsPage,
}
TOAST_COLORS = {
    "success": "#4f7f5b",
    "error": COLORS["danger"],
    "info": COLORS["accent"],
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # stay hidden until everything is built, so nothing flickers
        self.title("Student Attendance Management System")
        self.configure(bg=COLORS["background"])
        self.minsize(1020, 680)
        self._open_centered(1240, 800)
        apply_ttk_theme(self)

        self.session = auth.Session()
        self.pages = {}
        self.nav_buttons = {}
        self.current_page = None
        self._toast = None
        self._toast_job = None

        self._build_auth_area()
        self._build_shell()
        self.show_auth("login")
        self.deiconify()

    # -- window ------------------------------------------------------------
    def _open_centered(self, width, height):
        width = min(width, self.winfo_screenwidth() - 60)
        height = min(height, self.winfo_screenheight() - 100)
        x = (self.winfo_screenwidth() - width) // 2
        y = max((self.winfo_screenheight() - height) // 2 - 20, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        """Called by Tk for any error inside a button/key handler: show it instead of freezing."""
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        if isinstance(exc_value, mysql.connector.Error):
            messagebox.showerror(
                "Database error",
                f"{exc_value}\n\nMake sure MySQL is running in the XAMPP Control Panel.",
                parent=self,
            )
        else:
            messagebox.showerror("Something went wrong", str(exc_value), parent=self)

    # -- sign-in screens -----------------------------------------------------
    def _build_auth_area(self):
        self.auth_frame = tk.Frame(self, bg=COLORS["background"])
        self.auth_frame.grid_rowconfigure(0, weight=1)
        self.auth_frame.grid_columnconfigure(0, weight=1)
        self.auth_pages = {
            "login": LoginPage(self.auth_frame, self),
            "register": RegisterPage(self.auth_frame, self),
        }
        for page in self.auth_pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def show_auth(self, name):
        self.shell.pack_forget()
        self.auth_frame.pack(fill="both", expand=True)
        page = self.auth_pages[name]
        page.tkraise()
        page.on_show()

    def login_success(self, user):
        self.session.user = user
        self.user_label.configure(text=user["username"])
        self.show_page("dashboard")

    def sign_out(self):
        self.session.user = None
        self.current_page = None
        self.show_auth("login")

    # -- main application shell ---------------------------------------------
    def _build_shell(self):
        self.shell = tk.Frame(self, bg=COLORS["background"])
        self.shell.grid_rowconfigure(0, weight=1)
        self.shell.grid_columnconfigure(1, weight=1)

        sidebar = tk.Frame(self.shell, bg=COLORS["text"], width=232)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        content = tk.Frame(self.shell, bg=COLORS["background"])
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        for name, page_class in PAGES.items():
            page = page_class(content, self)
            page.grid(row=0, column=0, sticky="nsew")  # all pages share one cell
            self.pages[name] = page

    def _build_sidebar(self, sidebar):
        brand = tk.Frame(sidebar, bg=COLORS["text"])
        brand.pack(fill="x", padx=20, pady=(24, 30))
        logo = tk.Canvas(brand, width=52, height=52, bg=COLORS["text"], highlightthickness=0)
        logo.pack(side="left", padx=(0, 11))
        logo.create_oval(2, 2, 50, 50, fill=COLORS["terracotta"], outline="")
        logo.create_rectangle(17, 12, 35, 40, fill=COLORS["surface"], outline="")
        logo.create_line(21, 20, 31, 20, fill=COLORS["terracotta"], width=3)
        logo.create_line(21, 26, 31, 26, fill=COLORS["terracotta"], width=3)
        logo.create_line(20, 33, 24, 37, 33, 28, fill=COLORS["accent"], width=3)
        names = tk.Frame(brand, bg=COLORS["text"])
        names.pack(side="left")
        tk.Label(names, text="ATTENDANCE", bg=COLORS["text"], fg="#ffffff", font=font(10, "bold")).pack(anchor="w")
        tk.Label(names, text="MANAGEMENT", bg=COLORS["text"], fg=COLORS["sidebar_muted"],
                 font=font(8, "bold")).pack(anchor="w", pady=(2, 0))

        tk.Label(sidebar, text="WORKSPACE", bg=COLORS["text"], fg=COLORS["sidebar_muted"],
                 font=font(8, "bold")).pack(anchor="w", padx=22, pady=(0, 8))
        for name, label in NAVIGATION:
            button = tk.Button(
                sidebar, text=f"   {label}", anchor="w", relief="flat", bd=0, padx=15, pady=14,
                bg=COLORS["text"], fg=COLORS["sidebar_text"], activebackground=COLORS["accent_hover"],
                activeforeground="#ffffff", font=font(11), cursor="hand2",
                command=lambda n=name: self.show_page(n),
            )
            button.pack(fill="x", padx=12, pady=2)
            button.bind("<Enter>", lambda _e, n=name: self._hover_nav(n, True))
            button.bind("<Leave>", lambda _e, n=name: self._hover_nav(n, False))
            self.nav_buttons[name] = button

        # Bottom of the sidebar: who is signed in + sign out
        tk.Label(sidebar, text="Student Attendance System", bg=COLORS["text"], fg=COLORS["sidebar_muted"],
                 font=font(8)).pack(side="bottom", anchor="w", padx=22, pady=(0, 16))
        AppButton(sidebar, "SIGN OUT", self.sign_out, "secondary").pack(side="bottom", fill="x", padx=16, pady=(0, 10))
        self.user_label = tk.Label(sidebar, bg=COLORS["text"], fg="#ffffff", font=font(11, "bold"), anchor="w")
        self.user_label.pack(side="bottom", fill="x", padx=22)
        tk.Label(sidebar, text="SIGNED IN AS", bg=COLORS["text"], fg=COLORS["sidebar_muted"],
                 font=font(8, "bold"), anchor="w").pack(side="bottom", fill="x", padx=22, pady=(0, 2))

    def _hover_nav(self, name, inside):
        if name != self.current_page:
            self.nav_buttons[name].configure(bg=COLORS["sidebar_hover"] if inside else COLORS["text"])

    # -- navigation --------------------------------------------------------
    def show_page(self, name, **options):
        """Show a page and let it refresh itself. Extra options go to page.on_show()."""
        if not self.session.user:
            self.show_auth("login")
            return
        if not self.shell.winfo_manager():
            self.auth_frame.pack_forget()
            self.shell.pack(fill="both", expand=True)
        self.current_page = name
        for nav_name, button in self.nav_buttons.items():
            active = nav_name == name
            button.configure(
                bg=COLORS["accent"] if active else COLORS["text"],
                fg="#ffffff" if active else COLORS["sidebar_text"],
                font=font(11, "bold" if active else "normal"),
            )
        page = self.pages[name]
        page.tkraise()
        page.on_show(**options)

    # -- small "saved!" messages -------------------------------------------
    def toast(self, message, kind="success"):
        if self._toast is not None:
            self.after_cancel(self._toast_job)
            self._toast.destroy()
        self._toast = tk.Label(
            self, text=message, bg=TOAST_COLORS[kind], fg="#ffffff", font=font(10, "bold"), padx=18, pady=11
        )
        self._toast.place(relx=1.0, rely=1.0, x=-28, y=-28, anchor="se")
        self._toast.lift()
        self._toast_job = self.after(3000, self._hide_toast)

    def _hide_toast(self):
        if self._toast is not None:
            self._toast.destroy()
            self._toast = None


def main():
    try:
        db.init_db()
    except (database.DatabaseConfigurationError, mysql.connector.Error) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database error",
            f"{error}\n\nMake sure MySQL is running in the XAMPP Control Panel, then run the program again.",
            parent=root,
        )
        root.destroy()
        return
    App().mainloop()


if __name__ == "__main__":
    main()