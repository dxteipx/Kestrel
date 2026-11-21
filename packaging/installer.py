"""Kestrel's installer and uninstaller — one executable, two modes.

Installs per user into %LOCALAPPDATA%\\Programs\\Kestrel, so no administrator
rights are needed. The same executable is copied next to the app as
"Uninstall Kestrel.exe" and registered in Settings → Apps.

Modes:  (none) install wizard  ·  --uninstall  ·  --update (silent, used by the in-app updater)
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import winreg
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from kestrel import __author__, __repo__, __version__, icons, theme
from kestrel.config import CONFIG_DIR
from kestrel.core import shell
from kestrel.ui import art
from kestrel.ui import widgets as w

APP_EXE = "Kestrel.exe"
UNINSTALLER = "Uninstall Kestrel.exe"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Kestrel"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULT_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "Kestrel"
START_MENU = Path(os.environ.get("APPDATA", Path.home())) / r"Microsoft\Windows\Start Menu\Programs"

Report = Callable[[float, str], None]


# --- Install / uninstall logic ------------------------------------------------

@dataclass(frozen=True)
class Options:
    folder: Path
    desktop_shortcut: bool
    start_with_windows: bool


def payload_path() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "payload.zip"


def resolve_folder(chosen: str) -> Path:
    """Always install into a folder called Kestrel, never straight into e.g. the Desktop."""
    folder = Path(chosen.strip() or DEFAULT_DIR).expanduser()
    return folder if folder.name.lower() == "kestrel" else folder / "Kestrel"


def desktop_dir() -> Path:
    path = shell.powershell("[Environment]::GetFolderPath('Desktop')").strip()
    return Path(path) if path else Path.home() / "Desktop"


def is_running() -> bool:
    output = shell.run(["tasklist", "/FI", f"IMAGENAME eq {APP_EXE}", "/NH"]).stdout
    return APP_EXE.lower() in output.lower()


def _quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcut(link: Path, target: Path) -> None:
    shell.powershell(
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({_quote(link)});"
        f"$s.TargetPath = {_quote(target)}; $s.WorkingDirectory = {_quote(target.parent)};"
        f"$s.IconLocation = {_quote(f'{target},0')}; $s.Description = 'Kestrel - PC control center'; $s.Save()"
    )
    if not link.exists():
        raise OSError(f"Couldn't create the shortcut {link}")


def _folder_size_kb(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) // 1024


def register(folder: Path) -> None:
    exe = folder / APP_EXE
    strings = {
        "DisplayName": "Kestrel",
        "DisplayVersion": __version__,
        "Publisher": __author__,
        "DisplayIcon": str(exe),
        "InstallLocation": str(folder),
        "UninstallString": f'"{folder / UNINSTALLER}" --uninstall',
        "URLInfoAbout": __repo__,
    }
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE) as key:
        for name, value in strings.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, _folder_size_kb(folder))
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def set_start_with_windows(exe: Path | None) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if exe:
            winreg.SetValueEx(key, "Kestrel", 0, winreg.REG_SZ, f'"{exe}"')
        else:
            try:
                winreg.DeleteValue(key, "Kestrel")
            except FileNotFoundError:
                pass


def installed_folder() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            return Path(winreg.QueryValueEx(key, "InstallLocation")[0])
    except OSError:
        return None


def starts_with_windows() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, "Kestrel")
            return True
    except OSError:
        return False


def current_options() -> Options:
    """The choices of the existing install, so an update keeps them."""
    return Options(
        folder=installed_folder() or DEFAULT_DIR,
        desktop_shortcut=(desktop_dir() / "Kestrel.lnk").exists(),
        start_with_windows=starts_with_windows(),
    )


def wait_until_closed(timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while is_running():
        if time.monotonic() > deadline:
            raise RuntimeError("Kestrel didn't close, so it couldn't be updated. Close it and try again.")
        time.sleep(0.5)


def update(report: Report) -> Path:
    report(0.01, "Waiting for Kestrel to close…")
    wait_until_closed()
    return install(current_options(), report)


def install(options: Options, report: Report) -> Path:
    folder = options.folder
    report(0.02, "Getting ready…")
    if is_running():
        raise RuntimeError("Kestrel is open right now. Close it and try again.")

    if folder.exists():
        if (folder / APP_EXE).exists():
            report(0.04, "Removing the previous version…")
            shutil.rmtree(folder)
        elif any(folder.iterdir()):
            raise RuntimeError(f"{folder} already has other files in it. Pick an empty folder.")
    folder.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(payload_path()) as archive:
        members = archive.infolist()
        for index, member in enumerate(members, start=1):
            archive.extract(member, folder)
            if index % 20 == 0 or index == len(members):
                report(0.05 + 0.75 * index / len(members), f"Copying files  ·  {index} of {len(members)}")

    exe = folder / APP_EXE
    if getattr(sys, "frozen", False):
        report(0.84, "Adding the uninstaller…")
        shutil.copy2(sys.executable, folder / UNINSTALLER)

    report(0.88, "Creating shortcuts…")
    create_shortcut(START_MENU / "Kestrel.lnk", exe)
    if options.desktop_shortcut:
        create_shortcut(desktop_dir() / "Kestrel.lnk", exe)

    report(0.95, "Registering Kestrel with Windows…")
    register(folder)
    set_start_with_windows(exe if options.start_with_windows else None)
    report(1.0, "Done")
    return folder


def uninstall(remove_settings: bool, report: Report) -> Path:
    report(0.05, "Getting ready…")
    if is_running():
        raise RuntimeError("Kestrel is open right now. Close it and try again.")
    folder = installed_folder() or Path(sys.executable).parent

    report(0.25, "Removing shortcuts…")
    for link in (START_MENU / "Kestrel.lnk", desktop_dir() / "Kestrel.lnk"):
        link.unlink(missing_ok=True)

    report(0.45, "Cleaning up the registry…")
    set_start_with_windows(None)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass
    if remove_settings:
        shutil.rmtree(CONFIG_DIR, ignore_errors=True)

    report(0.7, "Removing files…")
    if (folder / APP_EXE).exists() or (folder / UNINSTALLER).exists():
        for child in folder.iterdir():
            if child.name == UNINSTALLER:
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
    report(1.0, "Done")
    return folder


def delete_after_exit(folder: Path) -> None:
    """The uninstaller can't delete itself while running, so cmd finishes the job."""
    if folder.name.lower() != "kestrel":
        return
    subprocess.Popen(
        f'cmd /c ping 127.0.0.1 -n 4 >nul & rmdir /s /q "{folder}"',
        cwd=tempfile.gettempdir(),
        creationflags=shell.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )


# --- Interface ----------------------------------------------------------------

def _checkbox(master, text: str, on: bool) -> ctk.CTkCheckBox:
    box = ctk.CTkCheckBox(master, text=text, font=theme.font(13), text_color=theme.TEXT, corner_radius=6,
                          checkbox_width=20, checkbox_height=20, border_width=2, border_color=theme.FAINT,
                          fg_color=theme.accent(), hover_color=theme.accent_hover())
    if on:
        box.select()
    return box


class SetupWindow(ctk.CTk):
    def __init__(self, mode: str = "install"):
        ctk.set_appearance_mode("Dark")
        theme.set_accent(theme.DEFAULT_ACCENT)
        super().__init__(fg_color=theme.SURFACE)
        icons.detect(self)
        theme.detect_fonts(self)
        art.set_scale(ctk.ScalingTracker.get_window_scaling(self))

        self.mode = mode
        self.title({"uninstall": "Uninstall Kestrel", "update": "Updating Kestrel"}.get(mode, "Kestrel Setup"))
        self.geometry("780x500")
        self.resizable(False, False)
        self._set_icon()

        start, end = theme.accent_pair()
        side = art.banner(250, 500, "Kestrel", f"Version {__version__}  ·  by {__author__}", start, end,
                          theme.resolve(theme.SIDEBAR))
        ctk.CTkLabel(self, text="", image=side).pack(side="left", fill="y")
        self.page = ctk.CTkFrame(self, fg_color="transparent")
        self.page.pack(side="left", fill="both", expand=True, padx=40, pady=36)

        self._messages: queue.Queue = queue.Queue()
        self._launch_after = None
        {"uninstall": self._confirm_uninstall, "update": self._update}.get(mode, self._welcome)()

    def _set_icon(self) -> None:
        try:
            path = Path(tempfile.gettempdir()) / "kestrel-setup.ico"
            art.write_icon(path, *theme.accent_pair())
            self.iconbitmap(str(path))
        except OSError:
            pass

    def _clear(self) -> None:
        for child in self.page.winfo_children():
            child.destroy()

    def _title(self, kicker: str, title: str, text: str) -> None:
        w.eyebrow(self.page, kicker).pack(anchor="w")
        w.heading(self.page, title, 30).pack(anchor="w", pady=(2, 6))
        w.muted(self.page, text, 13, wraplength=430).pack(anchor="w")

    def _footer(self) -> ctk.CTkFrame:
        footer = ctk.CTkFrame(self.page, fg_color="transparent")
        footer.pack(side="bottom", fill="x")
        return footer

    # --- Install ----------------------------------------------------------

    def _welcome(self) -> None:
        self._clear()
        self._title("Setup", "Install Kestrel",
                    "Live stats, cleanup, drivers, startup apps and a launcher for your apps and games — "
                    "all in one window.")

        w.label(self.page, "Install location", 12, "bold").pack(anchor="w", pady=(26, 6))
        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.pack(fill="x")
        self.location = ctk.CTkEntry(row, height=38, corner_radius=12, fg_color=theme.SURFACE_HI,
                                     border_color=theme.SURFACE_HI, text_color=theme.TEXT, font=theme.font(12))
        self.location.insert(0, str(installed_folder() or DEFAULT_DIR))
        self.location.pack(side="left", fill="x", expand=True)
        w.button(row, "Browse", self._browse).pack(side="left", padx=(8, 0))

        options = ctk.CTkFrame(self.page, fg_color="transparent")
        options.pack(fill="x", pady=(20, 0))
        self.desktop = _checkbox(options, "Create a desktop shortcut", True)
        self.startup = _checkbox(options, "Start Kestrel with Windows", False)
        self.launch = _checkbox(options, "Open Kestrel when setup finishes", True)
        for box in (self.desktop, self.startup, self.launch):
            box.pack(anchor="w", pady=5)

        footer = self._footer()
        w.muted(footer, "No administrator rights needed  ·  MIT License", 11).pack(side="left")
        w.button(footer, "Install", self._install, kind="primary", width=120).pack(side="right")
        w.button(footer, "Cancel", self.destroy, kind="ghost").pack(side="right", padx=(0, 8))

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title="Choose where to install Kestrel")
        if folder:
            self.location.delete(0, "end")
            self.location.insert(0, str(resolve_folder(folder)))

    def _install(self) -> None:
        options = Options(resolve_folder(self.location.get()), bool(self.desktop.get()), bool(self.startup.get()))
        self._launch_after = bool(self.launch.get())
        self._progress("Installing", "Installing Kestrel")
        self._run(lambda report: install(options, report), self._installed)

    def _installed(self, folder: Path) -> None:
        self._clear()
        self._title("All set", "Kestrel is ready",
                    f"Installed to {folder}. You'll find it in the Start menu, and you can remove it any time "
                    "from Settings → Apps.")
        footer = self._footer()

        def finish() -> None:
            if self._launch_after:
                subprocess.Popen([str(folder / APP_EXE)], cwd=str(folder))
            self.destroy()

        w.button(footer, "Open Kestrel" if self._launch_after else "Finish", finish, kind="primary",
                 width=140).pack(side="right")

    # --- Update -----------------------------------------------------------

    def _update(self) -> None:
        self._launch_after = True
        self._progress("Update", f"Updating to {__version__}")
        self._run(update, self._updated)

    def _updated(self, folder: Path) -> None:
        self._clear()
        self._title("Updated", f"Kestrel {__version__} is ready", "Reopening Kestrel…")
        subprocess.Popen([str(folder / APP_EXE)], cwd=str(folder))
        self.after(1500, self.destroy)

    # --- Uninstall --------------------------------------------------------

    def _confirm_uninstall(self) -> None:
        self._clear()
        self._title("Uninstall", "Remove Kestrel?",
                    "This removes the app, its shortcuts and its startup entry from this PC.")
        self.remove_settings = _checkbox(self.page, "Also delete my settings, pinned apps and custom games", False)
        self.remove_settings.pack(anchor="w", pady=(24, 0))
        footer = self._footer()
        w.button(footer, "Uninstall", self._uninstall, kind="primary", width=130).pack(side="right")
        w.button(footer, "Cancel", self.destroy, kind="ghost").pack(side="right", padx=(0, 8))

    def _uninstall(self) -> None:
        remove_settings = bool(self.remove_settings.get())
        self._progress("Uninstalling", "Removing Kestrel")
        self._run(lambda report: uninstall(remove_settings, report), self._uninstalled)

    def _uninstalled(self, folder: Path) -> None:
        self._clear()
        self._title("Done", "Kestrel was removed", "Thanks for trying it out.")
        footer = self._footer()

        def close() -> None:
            delete_after_exit(folder)
            self.destroy()

        w.button(footer, "Close", close, kind="primary", width=120).pack(side="right")

    # --- Shared -----------------------------------------------------------

    def _progress(self, kicker: str, title: str) -> None:
        self._clear()
        self._title(kicker, title, "This only takes a moment.")
        self.bar = w.GradientBar(self.page, 8, warn=False)
        self.bar.pack(fill="x", pady=(34, 10))
        self.status = w.muted(self.page, "Getting ready…", 12)
        self.status.pack(anchor="w")

    def _run(self, work: Callable[[Report], Path], on_done: Callable[[Path], None]) -> None:
        def worker() -> None:
            try:
                result = work(lambda fraction, text: self._messages.put(("progress", fraction, text)))
            except Exception as error:  # surfaced to the user, never swallowed
                self._messages.put(("error", str(error), None))
            else:
                self._messages.put(("done", result, None))

        threading.Thread(target=worker, daemon=True).start()
        self._poll(on_done)

    def _poll(self, on_done: Callable[[Path], None]) -> None:
        while not self._messages.empty():
            kind, value, text = self._messages.get()
            if kind == "progress":
                self.bar.set(value)
                self.status.configure(text=text)
            elif kind == "done":
                on_done(value)
                return
            else:
                self._failed(value)
                return
        self.after(50, lambda: self._poll(on_done))

    def _failed(self, message: str) -> None:
        self._clear()
        self._title("Something went wrong", "Setup couldn't finish", message)
        footer = self._footer()
        retry = {"uninstall": self._confirm_uninstall, "update": self._update}.get(self.mode, self._welcome)
        w.button(footer, "Try again", retry, kind="primary", width=120).pack(side="right")
        w.button(footer, "Close", self.destroy, kind="ghost").pack(side="right", padx=(0, 8))


def main() -> None:
    mode = "uninstall" if "--uninstall" in sys.argv else "update" if "--update" in sys.argv else "install"
    SetupWindow(mode).mainloop()


if __name__ == "__main__":
    main()
