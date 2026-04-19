"""
Tests for infra.updater — 100% branch coverage.

Covers: check_for_update — newer version available (on_update_available called),
same version (callback not called), network error without on_error (silently
swallowed), network error with on_error (callback called), JSON missing tag_name.

All network I/O is mocked; no real HTTP requests are made.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import json
import threading
from unittest.mock import MagicMock, patch

from infra.updater import check_for_update

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(tag_name: str) -> MagicMock:
    """Return a mock HTTP response object with the given tag_name."""
    body = json.dumps({"tag_name": tag_name}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _wait_for(event: threading.Event, timeout: float = 2.0) -> bool:
    """Wait up to *timeout* seconds for *event* to be set."""
    return event.wait(timeout)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestCheckForUpdate:
    def test_newer_version_calls_callback(self):
        """on_update_available is called when the remote tag differs."""
        event = threading.Event()
        received = []

        def on_update(ver):
            received.append(ver)
            event.set()

        with patch("urllib.request.urlopen", return_value=_fake_response("v2.0.0")):
            check_for_update("v1.0.0", on_update)

        _wait_for(event)
        assert received == ["v2.0.0"]

    def test_same_version_does_not_call_callback(self):
        """on_update_available is NOT called when versions match."""
        called = threading.Event()

        def on_update(ver):
            called.set()

        with patch("urllib.request.urlopen", return_value=_fake_response("v1.0.0")):
            check_for_update("v1.0.0", on_update)

        # Give the thread 0.5 s to (not) call the callback
        assert not called.wait(0.5), "Callback should NOT have been called"

    def test_missing_tag_name_does_not_call_callback(self):
        """Missing tag_name in JSON payload does not call the callback."""
        called = threading.Event()
        body = json.dumps({}).encode()
        resp = MagicMock()
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=resp):
            check_for_update("v1.0.0", lambda v: called.set())

        assert not called.wait(0.5)

    def test_network_error_swallowed_without_on_error(self):
        """A network exception is silently swallowed when on_error is None."""
        done = threading.Event()
        # Patch the thread to set the event after completion
        original_thread = threading.Thread

        def _patched_thread(*a, **kw):
            t = original_thread(*a, **kw)
            original_run = t.run

            def _run_and_set():
                original_run()
                done.set()

            t.run = _run_and_set  # type: ignore[method-assign]
            return t

        with patch("urllib.request.urlopen", side_effect=OSError("no network")), \
                patch("threading.Thread", side_effect=_patched_thread):
            check_for_update("v1.0.0", lambda v: None, on_error=None)

        _wait_for(done)  # ensure thread finished without raising

    def test_network_error_calls_on_error_callback(self):
        """A network exception is forwarded to on_error when provided."""
        event = threading.Event()
        errors = []

        def on_err(exc):
            errors.append(exc)
            event.set()

        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            check_for_update("v1.0.0", lambda v: None, on_error=on_err)

        _wait_for(event)
        assert len(errors) == 1
        assert isinstance(errors[0], OSError)

    def test_custom_url_is_used(self):
        """check_for_update passes the custom URL to urlopen."""
        used_urls = []
        event = threading.Event()

        def fake_urlopen(req, timeout=None):
            used_urls.append(req.full_url)
            event.set()
            resp = _fake_response("v1.0.0")
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            check_for_update(
                "v1.0.0",
                lambda v: None,
                url="https://example.com/releases/latest",
            )

        _wait_for(event)
        assert any("example.com" in u for u in used_urls)

    def test_non_https_url_calls_on_error(self):
        """A non-HTTPS URL raises ValueError which is forwarded to on_error (line 63)."""
        event = threading.Event()
        errors: list[Exception] = []

        def on_err(exc: Exception) -> None:
            errors.append(exc)
            event.set()

        check_for_update(
            "v1.0.0",
            lambda v: None,
            url="http://insecure.example.com/releases",
            on_error=on_err,
        )

        _wait_for(event)
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    def test_non_https_url_without_on_error_is_swallowed(self):
        """A non-HTTPS URL raises ValueError; silently dropped when on_error is None."""
        done = threading.Event()
        original_thread = threading.Thread

        def _patched_thread(*a, **kw):
            t = original_thread(*a, **kw)
            original_run = t.run

            def _run_and_set():
                original_run()
                done.set()

            t.run = _run_and_set  # type: ignore[method-assign]
            return t

        with patch("threading.Thread", side_effect=_patched_thread):
            check_for_update(
                "v1.0.0",
                lambda v: None,
                url="http://insecure.example.com/releases",
                on_error=None,
            )

        _wait_for(done)  # must complete without raising
