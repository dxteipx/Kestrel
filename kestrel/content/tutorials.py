"""Guides shown on the Tutorials page. Plain data, so they're easy to edit or translate."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Guide:
    title: str
    summary: str
    minutes: int
    level: str
    steps: tuple[str, ...]
    page: str | None = None
    action: str | None = None


GUIDES: tuple[Guide, ...] = (
    Guide(
        "Getting around Kestrel",
        "A two-minute tour of what each section does.",
        2, "Beginner",
        (
            "Dashboard shows live CPU, memory, storage and network use, plus quick fixes and your pinned apps.",
            "System & stats lists your hardware, every drive and the processes using the most CPU.",
            "Optimizer, Drivers and Startup are where you clean up and speed things up.",
            "Apps and Games are launchers — search, pin, or add anything Kestrel didn't find on its own.",
            "Press Ctrl + 1 to Ctrl + 9 to jump between sections without the mouse.",
        ),
        "dashboard", "Open Dashboard",
    ),
    Guide(
        "Updating drivers safely",
        "Get newer drivers from Windows Update without breaking anything.",
        5, "Beginner",
        (
            "Open Drivers and press “Back up drivers”. Pick an empty folder, ideally on another drive.",
            "Press “Check for updates”. Kestrel asks Windows Update which drivers have newer versions.",
            "Read the list. Graphics drivers from NVIDIA, AMD or Intel are often newer on the vendor's own site.",
            "Press “Install all” and accept the Windows prompt. A window shows the progress.",
            "Restart your PC when it's done, even if Windows doesn't ask.",
            "If something misbehaves, Device Manager → the device → Properties → Driver → Roll Back Driver.",
        ),
        "drivers", "Open Drivers",
    ),
    Guide(
        "A faster boot",
        "Stop apps you don't need from opening with Windows.",
        3, "Beginner",
        (
            "Open Startup. Everything listed launches each time you sign in.",
            "Turn off chat apps, game launchers and updaters you can open yourself when needed.",
            "Leave audio, touchpad, graphics and security software on.",
            "Not sure what something is? Use the folder button to see where it lives.",
            "Restart and notice the difference. You can switch anything back on at any time.",
        ),
        "startup", "Open Startup",
    ),
    Guide(
        "Freeing up disk space",
        "Win back gigabytes without touching your own files.",
        4, "Beginner",
        (
            "Open Optimizer and look at the badge next to “Clear temporary files” — that's what you'll get back.",
            "Run it. Files used in the last hour are skipped, so nothing you're working on breaks.",
            "Empty the Recycle Bin if you're sure you don't need anything in it.",
            "For more, open Apps → Disk Cleanup → “Clean up system files” to remove old Windows updates.",
            "Keep at least 15% of your system drive free — Windows slows down when it's nearly full.",
        ),
        "optimizer", "Open Optimizer",
    ),
    Guide(
        "Getting more FPS",
        "Simple, reversible tweaks that help most games.",
        5, "Intermediate",
        (
            "Plug laptops in. Most of them throttle the GPU on battery.",
            "Use Game boost on the Games page: Game Mode on, background recording off, fastest power plan.",
            "Update your graphics driver — new games often need it.",
            "Close browsers and launchers you aren't using. System & stats shows what's eating CPU.",
            "Inside the game, lower shadows and volumetrics first; they cost the most for the least.",
        ),
        "games", "Open Games",
    ),
    Guide(
        "Reading your stats",
        "What the numbers mean and when to worry.",
        3, "Beginner",
        (
            "CPU near 100% for minutes at a time means something is working hard — check Top processes.",
            "Memory above 85% means Windows starts using the disk as memory, which feels sluggish.",
            "Storage bars turn amber at 75% and red at 90%.",
            "Network shows live download speed; the arrow below is upload.",
            "Copy specs on the System page gives you a tidy summary to paste when asking for help.",
        ),
        "system", "Open System",
    ),
    Guide(
        "Contributing to Kestrel",
        "Kestrel is open source — here's how to help.",
        4, "Advanced",
        (
            "Fork the repository on GitHub and clone your fork.",
            "Create a virtual environment and run pip install -r requirements.txt.",
            "Start the app with python main.py. Platform logic lives in kestrel/core, the interface in kestrel/ui.",
            "New page? Subclass Page, then register it in NAVIGATION inside kestrel/app.py.",
            "Open a pull request describing what changed and why. Screenshots help a lot.",
        ),
        "settings", "Open Settings",
    ),
)
