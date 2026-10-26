"""Decorative artwork drawn on Tk canvases.

Every drawing is designed on a fixed "design grid" (for example 640 x 700).
`Scene` scales that grid to whatever size the canvas currently has, so the art
stays sharp and centred when the window is resized.
"""
from assets.theme import COLORS, FONT_FAMILY


class Scene:
    def __init__(self, canvas, width, height):
        canvas.delete("all")
        canvas_width = max(canvas.winfo_width(), 1)
        canvas_height = max(canvas.winfo_height(), 1)
        self.canvas = canvas
        self.scale = min(canvas_width / width, canvas_height / height)
        self.offset_x = (canvas_width - width * self.scale) / 2
        self.offset_y = (canvas_height - height * self.scale) / 2

    def point(self, x, y):
        return self.offset_x + x * self.scale, self.offset_y + y * self.scale

    def _style(self, options):
        options = dict(options)
        if "width" in options:
            options["width"] = max(1, options["width"] * self.scale)
        if "font" in options:
            family, size, *style = options["font"]
            options["font"] = (family, max(6, round(size * self.scale)), *style)
        return options

    def rect(self, x1, y1, x2, y2, **options):
        options.setdefault("outline", "")
        self.canvas.create_rectangle(*self.point(x1, y1), *self.point(x2, y2), **self._style(options))

    def oval(self, x1, y1, x2, y2, **options):
        options.setdefault("outline", "")
        self.canvas.create_oval(*self.point(x1, y1), *self.point(x2, y2), **self._style(options))

    def line(self, points, **options):
        options.setdefault("capstyle", "round")
        coordinates = [c for p in points for c in self.point(*p)]
        self.canvas.create_line(*coordinates, **self._style(options))

    def polygon(self, points, **options):
        options.setdefault("outline", "")
        coordinates = [c for p in points for c in self.point(*p)]
        self.canvas.create_polygon(*coordinates, **self._style(options))

    def text(self, x, y, value, **options):
        self.canvas.create_text(*self.point(x, y), text=value, **self._style(options))


def draw_person(scene, cx, top, size, skin, hair, jacket, trousers, long_hair=False):
    """A friendly flat-style person. (cx, top) is the head centre/top on the grid."""

    def pts(points):
        return [(cx + x * size, top + y * size) for x, y in points]

    def oval(x1, y1, x2, y2, fill):
        (a, b), (c, d) = pts([(x1, y1), (x2, y2)])
        scene.oval(a, b, c, d, fill=fill)

    def line(points, fill, width, **options):
        scene.line(pts(points), fill=fill, width=width * size, **options)

    def polygon(points, fill):
        scene.polygon(pts(points), fill=fill, smooth=True)

    white = "#f7f7f4"
    oval(-28, 162, 28, 172, "#ded8d0")  # shadow
    leg_start = 112 if long_hair else 103
    line([(-10, leg_start), (-11, 130), (-12, 148)], trousers, 12)
    line([(10, leg_start), (11, 130), (12, 148)], trousers, 12)
    oval(-23, 145, -5, 156, white)
    oval(5, 145, 23, 156, white)

    line([(-19, 65), (-27, 82), (-25, 100)], skin, 10, smooth=True)
    line([(19, 65), (27, 82), (25, 100)], skin, 10, smooth=True)
    oval(-29, 96, -21, 104, skin)
    oval(21, 96, 29, 104, skin)
    polygon([(-18, 56), (-11, 51), (11, 51), (18, 56), (24, 96), (19, 106), (-19, 106), (-24, 96)], jacket)
    polygon([(-10, 54), (0, 62), (10, 54), (7, 52), (-7, 52)], white)
    oval(-3, 75, 3, 81, white)
    oval(-3, 88, 3, 94, white)
    if long_hair:
        polygon([(-20, 95), (20, 95), (25, 119), (13, 124), (-13, 124), (-25, 119)], jacket)

    oval(-23, 11, -16, 31, skin)  # ears
    oval(16, 11, 23, 31, skin)
    oval(-24, 1, 24, 68, skin)  # face
    if long_hair:
        oval(-28, -1, 28, 82, hair)
        oval(-23, 7, 23, 68, skin)
        polygon([(-22, 22), (-17, 26), (-18, 65), (-24, 78), (-30, 71), (-29, 38)], hair)
        polygon([(22, 22), (17, 26), (18, 65), (24, 78), (30, 71), (29, 38)], hair)
        fringe = [(-26, 29), (-24, 14), (-13, 4), (0, 0), (14, 5), (25, 18), (23, 29), (14, 21), (6, 18), (-4, 20), (-14, 17), (-22, 27)]
        oval(16, 3, 28, 15, COLORS["terracotta"])
        oval(19, 6, 25, 12, COLORS["gold"])
    else:
        oval(-25, 0, 25, 38, hair)
        fringe = [(-24, 29), (-23, 13), (-13, 4), (0, 0), (14, 5), (24, 17), (23, 28), (14, 21), (6, 18), (-4, 20), (-14, 17), (-21, 27)]
    polygon(fringe, hair)

    oval(-11, 32, -5, 40, "#343b43")  # eyes
    oval(5, 32, 11, 40, "#343b43")
    oval(-9, 33, -7, 36, "#ffffff")
    oval(7, 33, 9, 36, "#ffffff")
    oval(-16, 43, -9, 48, "#e8a99b")  # cheeks
    oval(9, 43, 16, 48, "#e8a99b")
    line([(-5, 49), (0, 53), (5, 49)], "#875e4e", 2, smooth=True)  # smile


def _auth_background(scene):
    scene.rect(0, 0, 640, 700, fill=COLORS["surface_tint"])


def _bottom_dots(scene, x):
    scene.oval(x, 568, x + 138, 603, fill="#e7ddd1")
    for offset, color in ((21, COLORS["accent"]), (55, COLORS["terracotta"]), (89, COLORS["gold"])):
        scene.oval(x + offset, 574, x + offset + 21, 595, fill=color)


def draw_login_art(canvas):
    scene = Scene(canvas, 640, 700)
    _auth_background(scene)
    scene.oval(355, 247, 618, 510, fill=COLORS["accent_light"])
    scene.oval(17, 540, 190, 713, fill="#e9ddd0")

    for y, line_text, size in ((54, "Sign in to", 27), (94, "Student Attendance", 27), (134, "Management System", 27)):
        scene.text(48, y, line_text, anchor="nw", fill=COLORS["text"], font=(FONT_FAMILY, size, "bold"))
    scene.text(50, 186, "Simple, organized attendance for every class.", anchor="nw",
               fill=COLORS["text_secondary"], font=(FONT_FAMILY, 10))

    for x, y, radius, color in (
        (88, 291, 5, COLORS["terracotta"]), (542, 278, 4, COLORS["gold"]),
        (516, 570, 5, COLORS["accent"]), (83, 552, 4, COLORS["gold"]),
        (550, 459, 3, COLORS["terracotta"]), (122, 470, 3, COLORS["accent"]),
    ):
        scene.oval(x - radius, y - radius, x + radius, y + radius, fill=color)

    # Attendance sheet card
    scene.rect(137, 314, 506, 550, fill="#e1d2c3")
    scene.rect(120, 294, 489, 530, fill=COLORS["surface"], outline=COLORS["border"], width=2)
    scene.rect(120, 294, 489, 355, fill=COLORS["terracotta"])
    scene.rect(120, 345, 489, 368, fill=COLORS["terracotta_hover"])
    scene.text(304, 327, "CLASS ATTENDANCE", fill="#ffffff", font=(FONT_FAMILY, 12, "bold"))
    for x in (205, 404):
        scene.line([(x, 281), (x, 310)], fill=COLORS["terracotta_hover"], width=8)
        scene.oval(x - 7, 276, x + 7, 290, fill=COLORS["gold"])
    for row in range(3):
        y = 393 + row * 39
        for column in range(4):
            x = 155 + column * 78
            scene.rect(x, y, x + 57, y + 27, fill=COLORS["surface_alt"] if row % 2 == 0 else "#f3ede5",
                       outline=COLORS["border"])
            if column == 0:
                scene.line([(x + 15, y + 13), (x + 22, y + 19), (x + 42, y + 7)], fill=COLORS["accent"], width=3)
            else:
                scene.line([(x + 13, y + 14), (x + 43, y + 14)], fill="#d8cabc", width=2)

    # Clock badge
    scene.oval(438, 237, 532, 331, fill=COLORS["gold"])
    scene.oval(448, 247, 522, 321, fill=COLORS["surface"])
    scene.line([(485, 256), (485, 284), (507, 296)], fill=COLORS["accent"], width=5)
    scene.oval(478, 277, 492, 291, fill=COLORS["accent"])

    draw_person(scene, 116, 367, 0.92, "#c99e7c", COLORS["text"], COLORS["accent"], COLORS["text"])
    draw_person(scene, 500, 419, 0.82, "#edc6a6", COLORS["text_secondary"], COLORS["terracotta"],
                COLORS["text"], long_hair=True)
    _bottom_dots(scene, 251)


def draw_register_art(canvas):
    scene = Scene(canvas, 640, 700)
    _auth_background(scene)
    scene.oval(25, 38, 208, 221, fill="#e7ddd1")
    scene.oval(436, 482, 633, 679, fill=COLORS["accent_light"])

    scene.text(48, 68, "A welcoming space", anchor="nw", fill=COLORS["text"], font=(FONT_FAMILY, 25, "bold"))
    scene.text(50, 111, "for every class", anchor="nw", fill=COLORS["text"], font=(FONT_FAMILY, 25, "bold"))
    scene.text(52, 163, "Create an account to keep student records", anchor="nw",
               fill=COLORS["text_secondary"], font=(FONT_FAMILY, 10))
    scene.text(52, 184, "and daily attendance organized in one place.", anchor="nw",
               fill=COLORS["text_secondary"], font=(FONT_FAMILY, 10))

    scene.rect(139, 268, 516, 548, fill="#e1d2c3")
    scene.rect(120, 248, 497, 528, fill=COLORS["surface"], outline=COLORS["border"], width=2)
    scene.rect(120, 248, 497, 320, fill=COLORS["accent"])
    scene.text(153, 273, "YOUR ATTENDANCE WORKSPACE", anchor="nw", fill="#ffffff", font=(FONT_FAMILY, 10, "bold"))
    for index, (label, detail) in enumerate((
        ("Student profiles", "Keep course and section details together"),
        ("Daily attendance", "Record PRESENT, LATE or ABSENT per class"),
        ("Useful reports", "Review attendance when you need it"),
    )):
        y = 351 + index * 56
        scene.oval(151, y, 178, y + 27, fill=COLORS["accent_light"])
        scene.line([(158, y + 14), (163, y + 19), (172, y + 8)], fill=COLORS["accent"], width=3)
        scene.text(191, y - 2, label, anchor="nw", fill=COLORS["text"], font=(FONT_FAMILY, 10, "bold"))
        scene.text(191, y + 18, detail, anchor="nw", fill=COLORS["text_secondary"], font=(FONT_FAMILY, 8))

    draw_person(scene, 96, 436, 0.8, "#c99e7c", COLORS["text"], COLORS["accent"], COLORS["text"])
    draw_person(scene, 542, 400, 0.8, "#edc6a6", COLORS["text_secondary"], COLORS["terracotta"],
                COLORS["text"], long_hair=True)
    _bottom_dots(scene, 270)


def draw_board(canvas, selected_date):
    """Blackboard with the selected calendar date and a teacher (dashboard)."""
    scene = Scene(canvas, 470, 310)
    scene.oval(40, 26, 427, 300, fill=COLORS["surface_tint"])
    scene.rect(14, 44, 284, 224, fill=COLORS["border_strong"])
    scene.rect(23, 53, 275, 215, fill="#514237")
    scene.line([(36, 210), (262, 210)], fill=COLORS["gold"], width=3)
    scene.text(149, 103, "STUDENT ATTENDANCE", fill="#f4eee7", font=(FONT_FAMILY, 12, "bold"))
    scene.text(149, 128, "MANAGEMENT SYSTEM", fill="#d8cabc", font=(FONT_FAMILY, 9, "bold"))
    scene.text(149, 174, selected_date.strftime("%b %d, %Y"), fill="#ffffff", font=(FONT_FAMILY, 19, "bold"))
    scene.rect(119, 224, 179, 233, fill=COLORS["accent"])
    scene.rect(105, 233, 193, 242, fill=COLORS["border_strong"])
    draw_person(scene, 356, 73, 1.05, "#e8b997", COLORS["text"], COLORS["terracotta"],
                COLORS["text"], long_hair=True)
