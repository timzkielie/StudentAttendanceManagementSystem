"""Login and registration.

Part 1 (top):    the rules - password hashing, validation, sign-in, sign-up.
Part 2 (bottom): the two screens that use those rules.
"""
import hashlib
import hmac
import secrets
import tkinter as tk

from database import DatabaseManager
from assets.illustrations import draw_login_art, draw_register_art
from assets.theme import COLORS, font
from assets.widgets import AppButton, field_label, link_button, make_entry

# ===========================================================================
# Part 1 - rules
# ===========================================================================

db = DatabaseManager()  # always the same shared instance (Singleton)

MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 6
_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 310_000
_INVALID_LOGIN = "Invalid username or password."


class AuthError(Exception):
    """A problem the user can fix. The message is safe to show on screen."""


class Session:
    """Remembers who is signed in while the program is open."""

    def __init__(self):
        self.user = None  # {"id": ..., "username": ...} or None


def hash_password(password):
    """Salted PBKDF2 hash: 'algorithm$iterations$salt$digest'. Never store plain text."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """Return (is_valid, needs_upgrade). Old plain-text passwords still work once."""
    if not stored.startswith(f"{_ALGORITHM}$"):
        return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8")), True
    try:
        _algorithm, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(digest, bytes.fromhex(expected)), False
    except ValueError:
        return False, False


def authenticate(username, password):
    """Return {"id", "username"} for valid credentials, otherwise raise AuthError."""
    username = username.strip()
    if not username or not password:
        raise AuthError("Enter your username and password.")
    row = db.get_user(username)
    if row is None:
        raise AuthError(_INVALID_LOGIN)  # same message as a wrong password
    valid, needs_upgrade = verify_password(password, row["password"])
    if not valid:
        raise AuthError(_INVALID_LOGIN)
    if needs_upgrade:
        db.update_password_hash(row["id"], hash_password(password))
    return {"id": row["id"], "username": row["username"]}


def register_user(username, password, confirm):
    """Create an account or raise AuthError explaining what to fix."""
    username = username.strip()
    if not username or not password:
        raise AuthError("Username and password are required.")
    if len(username) < MIN_USERNAME_LENGTH:
        raise AuthError(f"Username must be at least {MIN_USERNAME_LENGTH} characters.")
    if not username.replace("_", "").replace(".", "").isalnum():
        raise AuthError("Username may only contain letters, numbers, dots and underscores.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirm:
        raise AuthError("Passwords do not match.")
    if db.create_user(username, hash_password(password)) is None:
        raise AuthError("That username is already taken.")


# ===========================================================================
# Part 2 - screens
# ===========================================================================
class _AuthPage(tk.Frame):
    """Card with an illustration on one side and a form on the other."""

    art_first = True  # login: art on the left; register: art on the right

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["background"])
        self.app = app
        card = tk.Frame(self, bg=COLORS["surface"])
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.96, relheight=0.94)
        card.grid_rowconfigure(0, weight=1)
        art_column, form_column = (0, 1) if self.art_first else (1, 0)
        card.grid_columnconfigure(art_column, weight=11, uniform="auth")
        card.grid_columnconfigure(form_column, weight=9, uniform="auth")

        art = tk.Canvas(card, bg=COLORS["surface_tint"], highlightthickness=0, takefocus=False)
        art.grid(row=0, column=art_column, sticky="nsew")
        art.bind("<Configure>", lambda _e: self.draw_art(art))

        panel = tk.Frame(card, bg=COLORS["surface"])
        panel.grid(row=0, column=form_column, sticky="nsew")
        form = tk.Frame(panel, bg=COLORS["surface"])
        form.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8)
        self.build_form(form)

    # -- helpers shared by both forms --------------------------------------
    def _title(self, form, title, subtitle):
        tk.Label(form, text=title, font=font(24, "bold"), bg=COLORS["surface"],
                 fg=COLORS["text"], anchor="w").pack(fill="x")
        tk.Label(form, text=subtitle, font=font(10), bg=COLORS["surface"],
                 fg=COLORS["text_secondary"], anchor="w").pack(fill="x", pady=(6, 24))

    def _entry(self, form, label, show=""):
        field_label(form, label, COLORS["surface"]).pack(anchor="w")
        entry = make_entry(form, show=show)
        entry.pack(fill="x", ipady=9, pady=(4, 14))
        entry.bind("<Return>", lambda _e: self.submit())
        return entry

    def _error_label(self, form):
        self.error = tk.Label(form, text="", font=font(9, "bold"), bg=COLORS["surface"],
                              fg=COLORS["danger"], anchor="w", justify="left", wraplength=360)
        self.error.pack(fill="x", pady=(4, 0))

    def _footer(self, form, prompt, link_text, command):
        row = tk.Frame(form, bg=COLORS["surface"])
        row.pack(anchor="w", pady=(16, 0))
        tk.Label(row, text=prompt, font=font(9), bg=COLORS["surface"],
                 fg=COLORS["text_secondary"]).pack(side="left")
        link_button(row, link_text, command).pack(side="left", padx=(4, 0))
        tk.Label(form, text="STUDENT ATTENDANCE MANAGEMENT SYSTEM", font=font(8, "bold"),
                 bg=COLORS["surface"], fg=COLORS["text_muted"]).pack(anchor="w", pady=(40, 0))

    def show_error(self, message):
        self.error.configure(text=message)

    # -- to be provided by LoginPage / RegisterPage ------------------------
    def draw_art(self, canvas):
        raise NotImplementedError

    def build_form(self, form):
        raise NotImplementedError

    def submit(self):
        raise NotImplementedError

    def on_show(self):
        pass


class LoginPage(_AuthPage):
    art_first = True

    def draw_art(self, canvas):
        draw_login_art(canvas)

    def build_form(self, form):
        self._title(form, "Welcome back", "Sign in to manage students and attendance.")
        self.username = self._entry(form, "USERNAME")
        self.password = self._entry(form, "PASSWORD", show="•")
        self.show_password = tk.BooleanVar(value=False)
        tk.Checkbutton(
            form, text="Show password", variable=self.show_password, command=self._toggle_password,
            bg=COLORS["surface"], activebackground=COLORS["surface"], fg=COLORS["text_secondary"],
            font=font(9), bd=0, highlightthickness=0, cursor="hand2",
        ).pack(anchor="w")
        self._error_label(form)
        AppButton(form, "SIGN IN", self.submit, large=True).pack(fill="x", pady=(10, 0))
        self._footer(form, "New to the system?", "Create an account",
                     lambda: self.app.show_auth("register"))

    def _toggle_password(self):
        self.password.configure(show="" if self.show_password.get() else "•")

    def submit(self):
        try:
            user = authenticate(self.username.get(), self.password.get())
        except AuthError as error:
            self.show_error(str(error))
            self.password.delete(0, "end")
            self.password.focus_set()
            return
        self.app.login_success(user)

    def prefill(self, username):
        self.username.delete(0, "end")
        self.username.insert(0, username)
        self.password.focus_set()

    def on_show(self):
        self.password.delete(0, "end")
        self.show_error("")
        self.show_password.set(False)
        self._toggle_password()
        (self.password if self.username.get() else self.username).focus_set()


class RegisterPage(_AuthPage):
    art_first = False

    def draw_art(self, canvas):
        draw_register_art(canvas)

    def build_form(self, form):
        self._title(form, "Create your account", "Set up your workspace to manage attendance.")
        self.username = self._entry(form, "USERNAME")
        self.password = self._entry(form, "PASSWORD", show="•")
        self.confirm = self._entry(form, "CONFIRM PASSWORD", show="•")
        tk.Label(form, text=f"Use at least {MIN_PASSWORD_LENGTH} characters for the password.",
                 font=font(9), bg=COLORS["surface"], fg=COLORS["text_muted"], anchor="w").pack(fill="x")
        self._error_label(form)
        AppButton(form, "CREATE ACCOUNT", self.submit, large=True).pack(fill="x", pady=(10, 0))
        self._footer(form, "Already have an account?", "Sign in",
                     lambda: self.app.show_auth("login"))

    def submit(self):
        username = self.username.get()
        try:
            register_user(username, self.password.get(), self.confirm.get())
        except AuthError as error:
            self.show_error(str(error))
            return
        self.app.show_auth("login")
        self.app.auth_pages["login"].prefill(username.strip())
        self.app.toast("Account created. You can sign in now.")

    def on_show(self):
        for entry in (self.username, self.password, self.confirm):
            entry.delete(0, "end")
        self.show_error("")
        self.username.focus_set()