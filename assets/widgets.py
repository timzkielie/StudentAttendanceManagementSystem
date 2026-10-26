"""Reusable building blocks so every page looks and behaves the same way."""
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk

from assets.theme import COLORS, STATUS_COLORS, font

# ---------------------------------------------------------------------------
# Buttons and entries
# ---------------------------------------------------------------------------
_BUTTON_KINDS = {
    # kind: (background, hover background, text colour)
    "primary": (COLORS["accent"], COLORS["accent_hover"], "#ffffff"),
    "secondary": (COLORS["surface_tint"], COLORS["border_strong"], COLORS["text"]),
    "danger": (COLORS["danger"], COLORS["danger_hover"], "#ffffff"),
    "success": (STATUS_COLORS["PRESENT"]["solid"], "#3f6849", "#ffffff"),
}


class AppButton(tk.Button):
    """Flat button with a hover effect. kind: primary, secondary, danger, success."""

    def __init__(self, parent, text, command, kind="primary", large=False, **options):
        bg, hover, fg = _BUTTON_KINDS[kind]
        padx, pady = (24, 13) if large else (18, 9)
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            disabledforeground=COLORS["text_muted"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=font(11 if large else 10, "bold"),
            padx=padx,
            pady=pady,
            **options,
        )
        self._normal_bg = bg
        self._hover_bg = hover
        self.bind("<Enter>", lambda _e: self._tint(self._hover_bg))
        self.bind("<Leave>", lambda _e: self._tint(self._normal_bg))

    def _tint(self, color):
        if str(self["state"]) != "disabled":
            self.configure(bg=color)

    def set_enabled(self, enabled):
        self.configure(
            state="normal" if enabled else "disabled",
            cursor="hand2" if enabled else "arrow",
            bg=self._normal_bg if enabled else COLORS["surface_tint"],
        )


def link_button(parent, text, command, bg=None):
    """Text-only button used for small links such as 'Create an account'."""
    bg = bg or parent.cget("bg")
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=COLORS["accent"],
        activebackground=bg,
        activeforeground=COLORS["accent_hover"],
        relief="flat",
        bd=0,
        cursor="hand2",
        font=font(9, "bold"),
    )


def make_entry(parent, show="", size=11, **options):
    """Text box with a border that turns brown while it has focus."""
    return tk.Entry(
        parent,
        show=show,
        font=font(size),
        relief="flat",
        bd=0,
        bg=COLORS["surface_alt"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        **options,
    )


def field_label(parent, text, bg=None):
    return tk.Label(
        parent,
        text=text,
        bg=bg or parent.cget("bg"),
        fg=COLORS["text"],
        font=font(9, "bold"),
    )


def make_clickable(widgets, command, normal=None, hover=None):
    """Make a group of widgets act like one big button with a hover colour."""
    normal = normal or COLORS["surface"]
    hover = hover or COLORS["accent_light"]

    def paint(color):
        for widget in widgets:
            widget.configure(bg=color)

    for widget in widgets:
        widget.bind("<Button-1>", lambda _e: command())
        widget.bind("<Enter>", lambda _e: paint(hover))
        widget.bind("<Leave>", lambda _e: paint(normal))


def center_window(window, parent, width, height):
    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    window.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")


# ---------------------------------------------------------------------------
# Page header and cards
# ---------------------------------------------------------------------------
def draw_page_icon(parent, name, size=64):
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=parent.cget("bg"),
        highlightthickness=0,
        takefocus=False,
    )
    canvas.create_oval(2, 2, size - 2, size - 2, fill=COLORS["accent_light"], outline="")
    scale = size / 48

    def xy(*values):
        return tuple(round(value * scale) for value in values)

    def line(points, color=COLORS["accent"], width=2):
        canvas.create_line(
            *[c for point in points for c in xy(*point)],
            fill=color,
            width=max(1, round(width * scale)),
            capstyle="round",
            joinstyle="round",
        )

    if name == "student":
        canvas.create_oval(*xy(18, 10, 30, 22), fill=COLORS["terracotta"], outline="")
        canvas.create_arc(
            *xy(11, 22, 37, 41),
            start=0,
            extent=180,
            style="arc",
            outline=COLORS["accent"],
            width=max(2, round(3 * scale)),
        )
        line([(14, 37), (34, 37)])
    elif name in {"attendance", "report"}:
        canvas.create_rectangle(
            *xy(12, 11, 36, 38),
            fill=COLORS["surface"],
            outline=COLORS["accent"],
            width=max(1, round(2 * scale)),
        )
        line([(18, 9), (18, 15)], COLORS["terracotta"], 3)
        line([(30, 9), (30, 15)], COLORS["terracotta"], 3)
        line([(17, 24), (21, 28), (28, 20)])
        line([(29, 25), (33, 25)], COLORS["gold"])
        line([(18, 33), (32, 33)], COLORS["border_strong"])
    else:  # dashboard
        canvas.create_rectangle(
            *xy(12, 11, 36, 37),
            fill=COLORS["surface"],
            outline=COLORS["accent"],
            width=max(1, round(2 * scale)),
        )
        line([(18, 18), (30, 18)], COLORS["terracotta"])
        line([(18, 24), (30, 24)])
        line([(18, 30), (26, 30)], COLORS["gold"])
    return canvas


def page_header(parent, title, subtitle, icon, size=64):
    """Icon + title + subtitle on the left, an empty `actions` frame on the right.

    Pack the returned frame yourself. Put buttons into `header.actions` and
    change the text later through `header.title_label` / `header.subtitle_label`.
    """
    bg = parent.cget("bg")
    header = tk.Frame(parent, bg=bg)
    draw_page_icon(header, icon, size).pack(side="left", padx=(0, 16))
    text = tk.Frame(header, bg=bg)
    text.pack(side="left")
    header.title_label = tk.Label(
        text, text=title, bg=bg, fg=COLORS["text"], font=font(19, "bold")
    )
    header.title_label.pack(anchor="w", pady=(1, 2))
    header.subtitle_label = tk.Label(
        text, text=subtitle, bg=bg, fg=COLORS["text_secondary"], font=font(10)
    )
    header.subtitle_label.pack(anchor="w")
    header.actions = tk.Frame(header, bg=bg)
    header.actions.pack(side="right")
    return header


def stat_card(parent, label, value="0", detail="", color=None):
    """Small number card. Update it with card.value_label / card.detail_label."""
    color = color or COLORS["accent"]
    card = tk.Frame(parent, bg=COLORS["surface"])
    tk.Frame(card, bg=color, width=5).pack(side="left", fill="y")
    body = tk.Frame(card, bg=COLORS["surface"], padx=16, pady=12)
    body.pack(side="left", fill="both", expand=True)
    tk.Label(
        body, text=label, bg=COLORS["surface"], fg=COLORS["text_secondary"], font=font(9, "bold")
    ).pack(anchor="w")
    card.value_label = tk.Label(
        body, text=value, bg=COLORS["surface"], fg=color, font=font(24, "bold")
    )
    card.value_label.pack(anchor="w", pady=(4, 0))
    card.detail_label = tk.Label(
        body, text=detail, bg=COLORS["surface"], fg=COLORS["text_secondary"], font=font(9)
    )
    card.detail_label.pack(anchor="w")
    return card


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
class DataTable(tk.Frame):
    """A table with a scrollbar, striped rows, coloured statuses and an empty message.

    columns: list of (key, heading, width, anchor).
    Every row needs a unique `iid` (for example the student ID). Read the
    selection with selected_iid(), NOT from the cell values: Tk turns values
    such as "0012" into the number 12, which would corrupt student IDs.
    """

    def __init__(self, parent, columns, empty_text="No records found.", height=12):
        super().__init__(parent, bg=COLORS["surface"])
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            columns=[column[0] for column in columns],
            show="headings",
            height=height,
            selectmode="browse",
        )
        for key, heading, width, anchor in columns:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=60, anchor=anchor)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("stripe", background=COLORS["surface_alt"])
        for status, colors in STATUS_COLORS.items():
            self.tree.tag_configure(status, foreground=colors["solid"], font=font(10, "bold"))

        self.empty_label = tk.Label(
            self.tree,
            text=empty_text,
            bg=COLORS["surface"],
            fg=COLORS["text_secondary"],
            font=font(11),
        )

    def set_empty_text(self, text):
        self.empty_label.configure(text=text)

    def set_rows(self, rows):
        """rows: iterable of (iid, values, status_or_None)."""
        self.tree.delete(*self.tree.get_children())
        count = 0
        for index, (iid, values, status) in enumerate(rows):
            tags = ["stripe"] if index % 2 else []
            if status:
                tags.append(status)
            self.tree.insert("", "end", iid=str(iid), values=values, tags=tags)
            count += 1
        if count:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.4, anchor="center")
        return count

    def selected_iid(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def on_open(self, callback):
        """Call callback(iid) on double-click or when Enter is pressed."""

        def double_click(event):
            iid = self.tree.identify_row(event.y)
            if iid:
                callback(iid)

        def enter(_event):
            iid = self.selected_iid()
            if iid:
                callback(iid)

        self.tree.bind("<Double-1>", double_click)
        self.tree.bind("<Return>", enter)


# ---------------------------------------------------------------------------
# Attendance-specific widgets
# ---------------------------------------------------------------------------
class StatusToggle(tk.Frame):
    """Three big buttons - PRESENT, LATE, ABSENT - where exactly one can be chosen."""

    def __init__(self, parent, bg, on_change=None):
        super().__init__(parent, bg=bg)
        self.value = None
        self._on_change = on_change
        self._labels = {}
        for status in STATUS_COLORS:
            label = tk.Label(
                self,
                text=status,
                width=9,
                padx=4,
                pady=7,
                font=font(9, "bold"),
                cursor="hand2",
            )
            label.pack(side="left", padx=(0, 6))
            label.bind("<Button-1>", lambda _e, s=status: self.set(s, notify=True))
            self._labels[status] = label
        self.set(None)

    def get(self):
        return self.value

    def set(self, value, notify=False):
        self.value = value
        for status, label in self._labels.items():
            if status == value:
                label.configure(bg=STATUS_COLORS[status]["solid"], fg="#ffffff")
            else:
                label.configure(bg=COLORS["surface_tint"], fg=COLORS["text_secondary"])
        if notify and self._on_change:
            self._on_change(value)


class DatePicker(tk.Frame):
    """[<] [ YYYY-MM-DD ] [>] [TODAY]. Calls on_change(date) for each valid new date."""

    def __init__(self, parent, initial=None, on_change=None):
        bg = parent.cget("bg")
        super().__init__(parent, bg=bg)
        self._on_change = on_change
        self._last = initial or date.today()
        self.var = tk.StringVar(value=self._last.isoformat())

        def arrow(text, days):
            return tk.Button(
                self, text=text, command=lambda: self._shift(days),
                bg=COLORS["surface_tint"], fg=COLORS["text"], activebackground=COLORS["border_strong"],
                relief="flat", bd=0, cursor="hand2", font=font(13, "bold"), width=2,
            )

        arrow("‹", -1).pack(side="left", ipady=2)
        self.entry = make_entry(self, size=11, textvariable=self.var, width=12, justify="center")
        self.entry.pack(side="left", padx=6, ipady=7)
        arrow("›", 1).pack(side="left", ipady=2)
        AppButton(self, "TODAY", lambda: self.set_date(date.today(), notify=True), "secondary").pack(
            side="left", padx=(8, 0)
        )
        self.entry.bind("<Return>", lambda _e: self._commit())
        self.entry.bind("<FocusOut>", lambda _e: self._commit())

    def get_date(self):
        try:
            return datetime.strptime(self.var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def set_date(self, value, notify=False):
        self.var.set(value.isoformat())
        self.entry.configure(fg=COLORS["text"])
        self._last = value
        if notify and self._on_change:
            self._on_change(value)

    def _shift(self, days):
        self.set_date((self.get_date() or date.today()) + timedelta(days=days), notify=True)

    def _commit(self):
        value = self.get_date()
        if value is None:
            self.entry.configure(fg=COLORS["danger"])
            return
        self.entry.configure(fg=COLORS["text"])
        if value != self._last:
            self._last = value
            if self._on_change:
                self._on_change(value)


class ScrollFrame(tk.Frame):
    """A vertically scrolling area. Put your widgets inside `.inner`."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inner.bind(
            "<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")

    def _pointer_inside(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget is self:
                return True
            widget = widget.master
        return False

    def _on_wheel(self, event):
        if not self.winfo_viewable() or not self._pointer_inside(event):
            return
        if event.num == 4:
            steps = -1
        elif event.num == 5:
            steps = 1
        else:
            steps = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(steps * 2, "units")

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)


class ClassPicker(tk.Frame):
    """Two-step chooser: pick a course card, then a section card.

    The data comes in through callables so this widget knows nothing about the
    database: load_courses() -> [{course, total, sections}],
    load_sections(course) -> [{section, total}], on_pick(course, section).
    """

    COLUMNS = 3

    def __init__(self, parent, load_courses, load_sections, on_pick, hint):
        bg = parent.cget("bg")
        super().__init__(parent, bg=bg)
        self._bg = bg
        self._load_courses = load_courses
        self._load_sections = load_sections
        self._on_pick = on_pick
        self._hint = hint
        self.course = None
        self._crumbs = tk.Frame(self, bg=bg)
        self._crumbs.pack(fill="x", pady=(0, 10))
        self._cards = tk.Frame(self, bg=bg)
        self._cards.pack(fill="x", anchor="n")

    def reload(self):
        if self.course:
            self.show_sections(self.course)
        else:
            self.show_courses()

    def show_courses(self):
        self.course = None
        self._set_crumbs()
        courses = self._load_courses()
        self._render(
            [
                (
                    item["course"],
                    f"{item['sections']} section(s)  ·  {item['total']} student(s)",
                    lambda name=item["course"]: self.show_sections(name),
                )
                for item in courses
            ],
            "No courses yet. Add students on the Students page first.",
        )

    def show_sections(self, course):
        self.course = course
        self._set_crumbs(course)
        sections = self._load_sections(course)
        self._render(
            [
                (
                    f"Section {item['section']}",
                    f"{item['total']} student(s)",
                    lambda name=item["section"]: self._on_pick(course, name),
                )
                for item in sections
            ],
            "This course has no sections.",
        )

    def _set_crumbs(self, course=None):
        for widget in self._crumbs.winfo_children():
            widget.destroy()
        if course:
            AppButton(self._crumbs, "‹  ALL COURSES", self.show_courses, "secondary").pack(
                side="left", padx=(0, 14)
            )
            tk.Label(
                self._crumbs, text=course, bg=self._bg, fg=COLORS["text"], font=font(15, "bold")
            ).pack(side="left")
            tk.Label(
                self._crumbs,
                text="  ·  choose a section",
                bg=self._bg,
                fg=COLORS["text_secondary"],
                font=font(10),
            ).pack(side="left")
        else:
            tk.Label(
                self._crumbs, text=self._hint, bg=self._bg, fg=COLORS["text_secondary"], font=font(10)
            ).pack(side="left")

    def _render(self, cards, empty_text):
        for widget in self._cards.winfo_children():
            widget.destroy()
        if not cards:
            tk.Label(
                self._cards, text=empty_text, bg=self._bg, fg=COLORS["text_secondary"], font=font(11)
            ).pack(pady=30)
            return
        for column in range(self.COLUMNS):
            self._cards.grid_columnconfigure(column, weight=1, uniform="picker")
        for index, (title, subtitle, command) in enumerate(cards):
            card = tk.Frame(self._cards, bg=COLORS["surface"], padx=20, pady=18, cursor="hand2")
            heading = tk.Label(
                card, text=title, bg=COLORS["surface"], fg=COLORS["text"],
                font=font(14, "bold"), anchor="w", cursor="hand2",
            )
            heading.pack(fill="x")
            detail = tk.Label(
                card, text=subtitle, bg=COLORS["surface"], fg=COLORS["text_secondary"],
                font=font(9), anchor="w", cursor="hand2",
            )
            detail.pack(fill="x", pady=(4, 0))
            make_clickable([card, heading, detail], command)
            card.grid(row=index // self.COLUMNS, column=index % self.COLUMNS, sticky="nsew", padx=6, pady=6)
