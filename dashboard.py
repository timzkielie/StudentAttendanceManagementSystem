"""Dashboard: totals, today's attendance at a glance, and a calendar shortcut."""
import tkinter as tk
from datetime import date

from tkcalendar import Calendar

from database import DatabaseManager
from assets.illustrations import draw_board
from assets.theme import COLORS, STATUS_COLORS, font
from assets.widgets import AppButton, page_header, stat_card


db = DatabaseManager()  # always the same shared instance (Singleton)

BACKGROUND = COLORS["background"]


class DashboardPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BACKGROUND)
        self.app = app

        self.header = page_header(
            self, "Welcome", "Manage courses, students, and daily attendance from one place.", "dashboard"
        )
        self.header.pack(fill="x", padx=28, pady=(22, 8))

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=28, pady=(4, 20))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3, uniform="dashboard")
        body.grid_columnconfigure(1, weight=2, uniform="dashboard")
        self._build_left(body)
        self._build_calendar(body)

    # -- layout ------------------------------------------------------------
    def _section_title(self, parent, text=""):
        label = tk.Label(parent, text=text, bg=BACKGROUND, fg=COLORS["text_secondary"], font=font(9, "bold"))
        label.pack(anchor="w", pady=(12, 8))
        return label

    def _card_row(self, parent, definitions):
        """definitions: [(key, label, detail, colour)] -> {key: card}"""
        row = tk.Frame(parent, bg=BACKGROUND)
        row.pack(fill="x")
        cards = {}
        for column, (key, label, detail, color) in enumerate(definitions):
            row.grid_columnconfigure(column, weight=1, uniform=f"cards{id(row)}")
            card = stat_card(row, label, "0", detail, color)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
            cards[key] = card
        return cards

    def _build_left(self, body):
        left = tk.Frame(body, bg=BACKGROUND)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))

        self._section_title(left, "OVERVIEW")
        self.overview = self._card_row(left, (
            ("students", "STUDENTS", "Registered", COLORS["accent"]),
            ("courses", "COURSES", "In the system", COLORS["terracotta"]),
            ("sections", "SECTIONS", "Course + section", COLORS["gold"]),
        ))

        self.today_title = self._section_title(left)
        solid = lambda status: STATUS_COLORS[status]["solid"]  # noqa: E731
        self.today = self._card_row(left, (
            ("PRESENT", "PRESENT", "marked today", solid("PRESENT")),
            ("LATE", "LATE", "marked today", solid("LATE")),
            ("ABSENT", "ABSENT", "marked today", solid("ABSENT")),
        ))

        self.art = tk.Canvas(left, bg=BACKGROUND, highlightthickness=0, takefocus=False)
        self.art.pack(fill="both", expand=True, pady=(10, 0))
        self.art.bind("<Configure>", lambda _e: self._draw_art())

    def _build_calendar(self, body):
        panel = tk.Frame(body, bg=COLORS["surface"], padx=22, pady=20)
        panel.grid(row=0, column=1, sticky="nsew")
        tk.Label(panel, text="ATTENDANCE CALENDAR", bg=COLORS["surface"],
                 fg=COLORS["text_secondary"], font=font(9, "bold")).pack(anchor="w")
        tk.Label(panel, text="Pick a day to review everyone's attendance.", bg=COLORS["surface"],
                 fg=COLORS["text_secondary"], font=font(9)).pack(anchor="w", pady=(2, 12))

        today = date.today()
        self.calendar = Calendar(
            panel,
            selectmode="day",
            year=today.year, month=today.month, day=today.day,
            date_pattern="yyyy-mm-dd",
            borderwidth=0,
            showweeknumbers=False,
            showothermonthdays=True,
            background=COLORS["accent"], foreground="#ffffff",
            bordercolor=COLORS["surface"],
            headersbackground=COLORS["surface_tint"], headersforeground=COLORS["text"],
            normalbackground=COLORS["surface"], normalforeground=COLORS["text"],
            weekendbackground=COLORS["surface_alt"], weekendforeground=COLORS["terracotta_hover"],
            othermonthbackground=COLORS["surface"], othermonthforeground=COLORS["text_muted"],
            othermonthwebackground=COLORS["surface"], othermonthweforeground=COLORS["text_muted"],
            selectbackground=COLORS["accent"], selectforeground="#ffffff",
            font=font(10), headersfont=font(9, "bold"),
            cursor="hand2",
        )
        self.calendar.pack(fill="both", expand=True)
        self.calendar.bind("<<CalendarSelected>>", lambda _e: self._draw_art())
        AppButton(panel, "VIEW ATTENDANCE FOR THIS DATE", self._view_selected_date, large=True).pack(
            fill="x", pady=(14, 0)
        )

    # -- behaviour ---------------------------------------------------------
    def on_show(self):
        user = self.app.session.user
        self.header.title_label.configure(text=f"Welcome, {user['username'] if user else 'User'}")

        totals = db.get_overview()
        for key, card in self.overview.items():
            card.value_label.configure(text=str(totals[key]))

        today = date.today()
        counts = db.get_attendance_counts(today)
        self.today_title.configure(text=f"TODAY  ·  {today:%b %d, %Y}".upper())
        for status, value in counts.items():
            self.today[status].value_label.configure(text=str(value))
        self._draw_art()

    def _draw_art(self):
        draw_board(self.art, self.calendar.selection_get())

    def _view_selected_date(self):
        self.app.show_page("reports", tab="date", date=self.calendar.selection_get())
