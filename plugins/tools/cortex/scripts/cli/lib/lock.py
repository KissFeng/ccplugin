"""Advisory file lock with cross-platform fallback.

`fcntl.flock` on macOS/Linux, no-op + stderr warn on Windows (P1 scope).
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from typing import Iterator

try:  # POSIX
    import fcntl  # type: ignore[import-not-found]

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - exercised only on Windows
    _HAS_FCNTL = False


@contextmanager
def file_lock(path: str, timeout: float = 5.0) -> Iterator[None]:
    """Advisory flock on `path` (creating it if missing).

    Raises `TimeoutError` if the lock cannot be acquired within `timeout`
    seconds. On Windows (no `fcntl`), prints a warning and yields without
    locking — P1 explicitly defers Windows support.
    """
    if not _HAS_FCNTL:
        print(
            f"cortex-mcp: fcntl unavailable, skipping flock on {path}",
            file=sys.stderr,
        )
        yield
        return

    flags = os.O_RDWR | os.O_CREAT
    fd = os.open(path, flags, 0o644)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"flock timeout on {path}") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
