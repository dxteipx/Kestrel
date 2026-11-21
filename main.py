import ctypes
import sys


def main() -> None:
    if sys.platform != "win32":
        sys.exit("Kestrel runs on Windows 10 and 11 only.")

    # Give Kestrel its own taskbar entry instead of grouping it under python.exe.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dxteipx.kestrel")

    from kestrel.app import KestrelApp

    KestrelApp().mainloop()


if __name__ == "__main__":
    main()
