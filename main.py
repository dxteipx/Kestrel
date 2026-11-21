import ctypes
import sys


def main() -> None:
    if sys.platform != "win32":
        sys.exit("Kestrel runs on Windows 10 and 11 only.")

    from kestrel import instance, log

    # A restart (new accent, admin mode, reset) briefly overlaps with the old window.
    if not instance.acquire(wait=8.0 if "--restart" in sys.argv else 0.0):
        instance.focus_existing()
        return

    log.setup()
    # Give Kestrel its own taskbar entry instead of grouping it under python.exe.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dxteipx.kestrel")

    from kestrel.app import KestrelApp

    KestrelApp().mainloop()


if __name__ == "__main__":
    main()
