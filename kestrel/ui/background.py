"""Run slow work off the UI thread and hand the result back safely.

Tk is not thread-safe, so workers never touch widgets. The main loop polls the
future and calls the callbacks itself.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="kestrel")


def run(
    widget,
    work: Callable[..., Any],
    *args,
    on_done: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> Future:
    future = _pool.submit(work, *args)

    def poll() -> None:
        if not widget.winfo_exists():
            return
        if not future.done():
            widget.after(80, poll)
            return
        error = future.exception()
        if error is not None:
            if on_error:
                on_error(error)
        elif on_done:
            on_done(future.result())

    widget.after(80, poll)
    return future
