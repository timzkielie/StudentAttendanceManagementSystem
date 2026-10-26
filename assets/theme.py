"""Colours, fonts and ttk styling shared by every screen.

Change a colour here and the whole application follows.
"""
from tkinter import ttk

COLORS = {
    "background": "#f4f0eb",
    "surface": "#fffdfa",
    "surface_alt": "#f8f4ef",
    "surface_tint": "#eee6dc",
    "border": "#e5dbd0",
    "border_strong": "#d8cabc",
    "text": "#3e3028",
    "text_secondary": "#76665b",
    "text_muted": "#a19489",
    "accent": "#896344",
    "accent_hover": "#704e37",
    "accent_light": "#f1e7dc",
    "terracotta": "#b9785c",
    "terracotta_hover": "#9d634c",
    "gold": "#c99d60",
    "danger": "#b04a43",
    "danger_hover": "#923a34",
    "sidebar_hover": "#54443a",
    "sidebar_text": "#f4eee7",
    "sidebar_muted": "#d0c2b4",
}

# One colour pair per attendance status: "solid" for text/buttons,
# "soft" for light backgrounds. The order here is the order shown on screen.
STATUS_COLORS = {
    "PRESENT": {"solid": "#4f7f5b", "soft": "#e3efe5"},
    "LATE": {"solid": "#b8862f", "soft": "#f6ecd6"},
    "ABSENT": {"solid": "#b04a43", "soft": "#f5e1df"},
}

FONT_FAMILY = "Segoe UI"


def font(size=10, weight="normal"):
    return (FONT_FAMILY, size, weight)


def apply_ttk_theme(root):
    """Style the ttk widgets (tables, drop-downs, scrollbars) once at start-up."""
    c = COLORS
    style = ttk.Style(root)
    style.theme_use("clam")  # the only built-in theme that honours custom colours

    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Treeview",
        background=c["surface"],
        fieldbackground=c["surface"],
        foreground=c["text"],
        rowheight=36,
        borderwidth=0,
        relief="flat",
        font=font(10),
    )
    style.configure(
        "Treeview.Heading",
        background=c["surface_tint"],
        foreground=c["text"],
        font=font(10, "bold"),
        padding=(10, 9),
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", c["accent_light"])],
        foreground=[("selected", c["text"])],
    )
    style.map("Treeview.Heading", background=[("active", c["border"])])

    style.configure(
        "TCombobox",
        fieldbackground=c["surface_alt"],
        background=c["surface_tint"],
        foreground=c["text"],
        arrowcolor=c["accent"],
        bordercolor=c["border"],
        lightcolor=c["surface_alt"],
        darkcolor=c["surface_alt"],
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", c["surface_alt"])],
        foreground=[("readonly", c["text"])],
        selectbackground=[("readonly", c["surface_alt"])],
        selectforeground=[("readonly", c["text"])],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=c["border_strong"],
        troughcolor=c["background"],
        bordercolor=c["background"],
        arrowcolor=c["text_secondary"],
        relief="flat",
    )

    root.option_add("*TCombobox*Listbox.font", font(10))
    root.option_add("*TCombobox*Listbox.background", c["surface"])
    root.option_add("*TCombobox*Listbox.foreground", c["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
