"""Build Kestrel.exe and the installer.

    python packaging/build.py

Produces dist/Kestrel-Setup-<version>.exe. Needs PyInstaller (pip install pyinstaller).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kestrel import __author__, __version__, theme  # noqa: E402
from kestrel.ui import art  # noqa: E402

BUILD = ROOT / "build"
# Optional imports Pillow and friends pull in, which Kestrel never uses.
EXCLUDES = ("numpy", "charset_normalizer", "unittest", "pydoc", "xmlrpc")
DIST = ROOT / "dist"
ICON = BUILD / "kestrel.ico"
PAYLOAD = BUILD / "payload.zip"

_VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}), prodvers=({v}), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1,
                    subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{author}'),
      StringStruct('FileDescription', '{description}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('ProductName', 'Kestrel'),
      StringStruct('ProductVersion', '{version}'),
      StringStruct('LegalCopyright', 'MIT License - {author}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"""


def version_file(name: str, description: str) -> Path:
    numbers = ", ".join((__version__.split(".") + ["0", "0", "0"])[:4])
    path = BUILD / f"{name}-version.txt"
    path.write_text(_VERSION_INFO.format(v=numbers, author=__author__, description=description,
                                         version=__version__), encoding="utf-8")
    return path


def pyinstaller(*args: str) -> None:
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
               "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
               *(arg for module in EXCLUDES for arg in ("--exclude-module", module)), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def build_app() -> Path:
    print("> Building Kestrel.exe")
    pyinstaller(
        "--name", "Kestrel", "--windowed", "--onedir",
        "--icon", str(ICON),
        "--version-file", str(version_file("app", "Kestrel - PC control center")),
        "--collect-data", "customtkinter",
        "--distpath", str(BUILD / "app"),
        str(ROOT / "main.py"),
    )
    return BUILD / "app" / "Kestrel"


def zip_payload(app_dir: Path) -> None:
    print("> Packing payload")
    with zipfile.ZipFile(PAYLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(app_dir.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(app_dir))


def build_installer() -> Path:
    print("> Building the installer")
    name = f"Kestrel-Setup-{__version__}"
    pyinstaller(
        "--name", name, "--windowed", "--onefile",
        "--icon", str(ICON),
        "--version-file", str(version_file("setup", "Kestrel Setup")),
        "--collect-data", "customtkinter",
        "--add-data", f"{PAYLOAD};.",
        "--paths", str(ROOT),
        "--distpath", str(DIST),
        str(ROOT / "packaging" / "installer.py"),
    )
    return DIST / f"{name}.exe"


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    art.write_icon(ICON, *theme.ACCENTS[theme.DEFAULT_ACCENT])
    app_dir = build_app()
    zip_payload(app_dir)
    setup = build_installer()
    shutil.rmtree(BUILD / "work", ignore_errors=True)
    print(f"\nDone: {setup.relative_to(ROOT)}  ({setup.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
