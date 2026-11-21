"""The sign-in / create-account screen shown before the main window."""

from __future__ import annotations

from typing import Callable

import threading

import customtkinter as ctk

from kestrel import cloud, theme
from kestrel.core import account, oauth
from kestrel.core.account import Session
from kestrel.ui import art, background
from kestrel.ui import widgets as w

_FORM_WIDTH = 360
_BRAND_COLORS = {"discord": "#5865F2"}


def _entry(master, placeholder: str, secret: bool = False) -> ctk.CTkEntry:
    entry = ctk.CTkEntry(master, width=_FORM_WIDTH, height=44, corner_radius=12, placeholder_text=placeholder,
                         show="•" if secret else "", fg_color=theme.SURFACE_HI, border_color=theme.SURFACE_HI,
                         border_width=1, text_color=theme.TEXT, placeholder_text_color=theme.FAINT,
                         font=theme.font(13))
    entry.bind("<FocusIn>", lambda _e: entry.configure(border_color=theme.accent()))
    entry.bind("<FocusOut>", lambda _e: entry.configure(border_color=theme.SURFACE_HI))
    return entry


def _link(master, text: str, command: Callable) -> ctk.CTkLabel:
    link = ctk.CTkLabel(master, text=text, font=theme.font(12, "bold"), text_color=theme.accent_end(),
                        cursor="hand2")
    link.bind("<Button-1>", lambda _e: command())
    return link


class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, on_signed_in: Callable[[Session], None], on_skip: Callable[[], None],
                 allow_skip: bool = not cloud.REQUIRE_ACCOUNT):
        super().__init__(master, fg_color=theme.BG)
        self._on_signed_in, self._on_skip = on_signed_in, on_skip
        self._mode = "signin"
        self._busy = False

        card = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=26, border_width=1,
                            border_color=theme.BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        start, end = theme.accent_pair()
        side = art.banner(330, 560, "Kestrel", "Your PC, calmly in control", start, end,
                          theme.resolve(theme.SIDEBAR), radius=20)
        ctk.CTkLabel(card, text="", image=side, fg_color="transparent").pack(side="left", padx=10, pady=10)

        form = ctk.CTkFrame(card, fg_color="transparent", width=_FORM_WIDTH)
        form.pack(side="left", fill="y", padx=(36, 46), pady=36)

        w.eyebrow(form, "Welcome").pack(anchor="w")
        self.title = w.heading(form, "Sign in to Kestrel", 28)
        self.title.pack(anchor="w", pady=(2, 4))
        self.subtitle = w.muted(form, "Keep your setup with you on every PC.", 13, wraplength=_FORM_WIDTH)
        self.subtitle.pack(anchor="w", pady=(0, 18))

        self.tabs = ctk.CTkSegmentedButton(
            form, values=["Sign in", "Create account"], command=self._switch, width=_FORM_WIDTH, height=36,
            font=theme.font(13), corner_radius=12, selected_color=theme.accent(),
            selected_hover_color=theme.accent_hover(), unselected_color=theme.SURFACE_HI,
            unselected_hover_color=theme.SURFACE_HOVER, fg_color=theme.SURFACE_HI, text_color=theme.TEXT,
        )
        self.tabs.set("Sign in")
        self.tabs.pack(anchor="w", pady=(0, 18))

        self.email = _entry(form, "Email")
        self.email.pack(anchor="w", pady=(0, 10))
        self.password = _entry(form, "Password", secret=True)
        self.password.pack(anchor="w")
        self.confirm = _entry(form, "Confirm password", secret=True)

        self.extras = ctk.CTkFrame(form, fg_color="transparent", width=1, height=1)
        self.extras.pack(fill="x", pady=(8, 0))
        self.forgot = _link(self.extras, "Forgot password?", self._forgot)
        self.forgot.pack(side="right")

        self.message = w.label(form, "", 12, wraplength=_FORM_WIDTH)
        self.message.pack(anchor="w", pady=(10, 6))

        self.submit = w.GradientButton(form, "Sign in", self._submit, width=_FORM_WIDTH, height=44)
        self.submit.pack(anchor="w")

        self._cancel_oauth: threading.Event | None = None
        self.provider_buttons: list[ctk.CTkButton] = []
        providers = [p for p in cloud.OAUTH_PROVIDERS if p in oauth.PROVIDER_NAMES]
        if providers:
            separator = ctk.CTkFrame(form, fg_color="transparent", width=_FORM_WIDTH, height=20)
            separator.pack(anchor="w", pady=(16, 12))
            separator.pack_propagate(False)
            ctk.CTkFrame(separator, width=118, height=1, fg_color=theme.BORDER).pack(side="left")
            w.muted(separator, "or continue with", 11, anchor="center").pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(separator, width=118, height=1, fg_color=theme.BORDER).pack(side="right")

            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(anchor="w")
            gap = 8
            width = (_FORM_WIDTH - gap * (len(providers) - 1)) // len(providers)
            for index, provider in enumerate(providers):
                icon_color = _BRAND_COLORS.get(provider) or theme.resolve(theme.TEXT)
                button = w.button(row, oauth.PROVIDER_NAMES[provider], lambda p=provider: self._oauth(p),
                                  width=width, image=art.brand_icon(provider, 18, icon_color), compound="left")
                button.pack(side="left", padx=(0 if index == 0 else gap, 0))
                self.provider_buttons.append(button)

        if allow_skip:
            w.divider(form, pady=16)
            w.button(form, "Continue without an account", self._on_skip, kind="ghost",
                     width=_FORM_WIDTH).pack(anchor="w")

        for entry in (self.email, self.password, self.confirm):
            entry.bind("<Return>", lambda _e: self._submit())
        self.after(150, self.email.focus_set)

    # --- Modes ------------------------------------------------------------

    def _switch(self, choice: str) -> None:
        self._mode = "signup" if choice == "Create account" else "signin"
        self._show("")
        if self._mode == "signup":
            self.title.configure(text="Create your account")
            self.subtitle.configure(text="Free, and takes a few seconds.")
            self.confirm.pack(anchor="w", pady=(10, 0), after=self.password)
            self.forgot.pack_forget()
            self.submit.configure(text="Create account")
        else:
            self.title.configure(text="Sign in to Kestrel")
            self.subtitle.configure(text="Keep your setup with you on every PC.")
            self.confirm.pack_forget()
            self.forgot.pack(side="right")
            self.submit.configure(text="Sign in")

    def _show(self, text: str, kind: str = "error") -> None:
        color = {"error": theme.DANGER, "success": theme.SUCCESS, "info": theme.MUTED}[kind]
        self.message.configure(text=text, text_color=color)

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self._busy = busy
        idle = "Create account" if self._mode == "signup" else "Sign in"
        self.submit.configure(state="disabled" if busy else "normal", text=text if busy else idle)
        for button in self.provider_buttons:
            button.configure(state="disabled" if busy else "normal")

    # --- Actions ----------------------------------------------------------

    def _submit(self) -> None:
        if self._busy:
            return
        email, password = self.email.get().strip(), self.password.get()
        try:
            account.validate(email, password)
        except account.AuthError as error:
            self._show(str(error))
            return

        if self._mode == "signup":
            if password != self.confirm.get():
                self._show("The passwords don't match.")
                return
            self._set_busy(True, "Creating account…")
            background.run(self, account.sign_up, email, password, on_done=self._signed_up, on_error=self._failed)
        else:
            self._set_busy(True, "Signing in…")
            background.run(self, account.sign_in, email, password, on_done=self._on_signed_in,
                           on_error=self._failed)

    def _signed_up(self, session: Session | None) -> None:
        if session is not None:
            self._on_signed_in(session)
            return
        self._set_busy(False)
        self.tabs.set("Sign in")
        self._switch("Sign in")
        self._show("Account created! Open the link we emailed you, then sign in here.", "success")

    def _failed(self, error: Exception) -> None:
        self._set_busy(False)
        self._show(str(error) if isinstance(error, account.AuthError) else "Something went wrong. Try again.")

    def _oauth(self, provider: str) -> None:
        if self._busy:
            return
        name = oauth.PROVIDER_NAMES[provider]
        self._cancel_oauth = threading.Event()
        self._set_busy(True, "Waiting for the browser…")
        self._show(f"Finish signing in with {name} in your browser. Press Esc to cancel.", "info")
        self.winfo_toplevel().bind("<Escape>", lambda _e: self._cancel())
        background.run(self, oauth.sign_in, provider, self._cancel_oauth,
                       on_done=self._oauth_done, on_error=self._oauth_failed)

    def _cancel(self) -> None:
        if self._cancel_oauth is not None:
            self._cancel_oauth.set()

    def _oauth_done(self, session: Session) -> None:
        self.winfo_toplevel().unbind("<Escape>")
        self._on_signed_in(session)

    def _oauth_failed(self, error: Exception) -> None:
        self.winfo_toplevel().unbind("<Escape>")
        self._failed(error)

    def _forgot(self) -> None:
        email = self.email.get().strip()
        self._show("Sending…", "info")
        background.run(self, account.send_password_reset, email,
                       on_done=lambda _r: self._show(f"If {email} has an account, a reset link is on its way.",
                                                     "success"),
                       on_error=self._failed)
