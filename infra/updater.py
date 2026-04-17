"""
Background update checker.

Fetches the latest GitHub release tag in a daemon thread and invokes a
callback on the calling thread when a newer version is available.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.0
"""

from __future__ import annotations

import json
import threading
import urllib.request
from typing import Callable, Optional


_GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/aminekhettat/Back-Office-Player/releases/latest"
)
_USER_AGENT = "BOP-update-checker/1.0"
_TIMEOUT = 5  # seconds


def check_for_update(
    current_version: str,
    on_update_available: Callable[[str], None],
    url: str = _GITHUB_RELEASES_URL,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> None:
    """
    Start a background daemon thread that checks GitHub for a newer release.

    If a newer tag is found (i.e. *tag_name* differs from *current_version*),
    *on_update_available* is called **from the background thread** with the
    latest tag string.  Callers that need to update the UI must marshal the
    call back to the main thread (e.g. via ``QTimer.singleShot``).

    Network errors are silently swallowed unless *on_error* is provided.

    Parameters
    ----------
    current_version : str
        The version string of the running application (e.g. ``"v1.0.0"``).
    on_update_available : callable
        Invoked with the latest release tag when a newer version exists.
    url : str, optional
        GitHub releases API URL.  Defaults to the BOP repository.
    on_error : callable, optional
        Invoked with the caught exception on network/parsing errors.
    """

    def _worker() -> None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "")
            if latest and latest != current_version:
                on_update_available(latest)
        except Exception as exc:
            if on_error is not None:
                on_error(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
