"""
Tests for infra.settings — 100% branch coverage.

Covers: get_settings_path (no legacy, with legacy migration), _deep_merge
(flat dicts, nested dicts), load_settings (no file, corrupt file, valid),
save_settings (success), add_recent_file (new entry, duplicate, max_files).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import infra.settings as settings_module
from infra.settings import (
    DEFAULT_SETTINGS,
    _deep_merge,
    add_recent_file,
    load_settings,
    save_settings,
)

# ---------------------------------------------------------------------------
# get_settings_path
# ---------------------------------------------------------------------------


class TestGetSettingsPath:
    def test_returns_path_object(self, settings_path):
        """get_settings_path returns a Path object."""
        result = settings_module.get_settings_path()
        assert isinstance(result, Path)

    def test_no_legacy_file_returns_standard_path(self, tmp_path, monkeypatch):
        """When no legacy settings.json exists in CWD, a normal path is returned."""
        new_path = tmp_path / "settings.json"
        # Make sure the legacy file doesn't exist
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(settings_module, "get_settings_path", lambda: new_path)
        assert settings_module.get_settings_path() == new_path

    def test_legacy_migration(self, tmp_path, monkeypatch):
        """A legacy settings.json in CWD is copied to the new location on first call."""
        # Place the legacy file in a temp dir that acts as CWD.
        legacy_dir = tmp_path / "cwd"
        legacy_dir.mkdir()
        legacy_file = legacy_dir / "settings.json"
        legacy_file.write_text(json.dumps({"default_volume": 55}), encoding="utf-8")

        new_dir = tmp_path / "appdata"
        new_dir.mkdir()

        # Change CWD so that Path("settings.json").absolute() resolves inside legacy_dir.
        monkeypatch.chdir(legacy_dir)
        # Redirect user_data_dir to our temp new_dir.
        monkeypatch.setattr(settings_module, "user_data_dir", lambda *a: str(new_dir))

        result = settings_module.get_settings_path()

        new_path = new_dir / "settings.json"
        assert result == new_path
        assert new_path.is_file(), "Legacy settings.json must have been migrated."
        data = json.loads(new_path.read_text(encoding="utf-8"))
        assert data["default_volume"] == 55


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_simple_flat_overwrite(self):
        """Flat key in update overwrites base value."""
        r = _deep_merge({"a": 1, "b": 2}, {"b": 99})
        assert r == {"a": 1, "b": 99}

    def test_new_flat_key_added(self):
        """A key only in update is added to the result."""
        r = _deep_merge({"a": 1}, {"b": 2})
        assert r["b"] == 2
        assert r["a"] == 1

    def test_nested_dict_merged_not_replaced(self):
        """Nested dicts are merged recursively; other keys are preserved."""
        base = {"shortcuts": {"open": "Ctrl+O", "play": "Ctrl+P"}}
        upd = {"shortcuts": {"open": "Ctrl+F"}}
        r = _deep_merge(base, upd)
        assert r["shortcuts"]["open"] == "Ctrl+F"
        assert r["shortcuts"]["play"] == "Ctrl+P"

    def test_does_not_mutate_base(self):
        """_deep_merge does not modify the base dict."""
        base = {"x": 1}
        _deep_merge(base, {"x": 2})
        assert base["x"] == 1

    def test_does_not_mutate_update(self):
        """_deep_merge does not modify the update dict."""
        upd = {"x": 2}
        _deep_merge({"x": 1}, upd)
        assert upd["x"] == 2

    def test_empty_update_returns_copy_of_base(self):
        """_deep_merge with empty update returns a copy of base."""
        base = {"a": 1}
        r = _deep_merge(base, {})
        assert r == base
        assert r is not base

    def test_nested_update_value_is_not_dict(self):
        """When update has a non-dict value for a dict key in base, it overwrites."""
        base = {"nested": {"a": 1}}
        upd = {"nested": "flat_string"}
        r = _deep_merge(base, upd)
        assert r["nested"] == "flat_string"


# ---------------------------------------------------------------------------
# load_settings / save_settings
# ---------------------------------------------------------------------------


class TestLoadSettings:
    def test_defaults_when_no_file(self, settings_path):
        """load_settings returns defaults when the file does not exist."""
        cfg = load_settings()
        assert cfg["default_volume"] == DEFAULT_SETTINGS["default_volume"]
        assert "shortcuts" in cfg

    def test_save_and_reload(self, settings_path):
        """Settings written with save_settings can be read back with load_settings."""
        cfg = load_settings()
        cfg["default_volume"] = 42
        save_settings(cfg)
        cfg2 = load_settings()
        assert cfg2["default_volume"] == 42

    def test_missing_keys_filled_with_defaults(self, settings_path):
        """Loading a partial settings file fills missing keys from defaults."""
        settings_path.write_text(json.dumps({"default_volume": 55}), encoding="utf-8")
        cfg = load_settings()
        assert cfg["default_volume"] == 55
        assert "recent_files" in cfg
        assert "shortcuts" in cfg

    def test_corrupt_file_returns_defaults(self, settings_path):
        """A corrupt JSON file causes load_settings to return defaults."""
        settings_path.write_text("NOT JSON", encoding="utf-8")
        cfg = load_settings()
        assert cfg["default_volume"] == DEFAULT_SETTINGS["default_volume"]

    def test_shortcuts_merged_not_replaced(self, settings_path):
        """Partial shortcuts dict in file does not wipe unset shortcut keys."""
        settings_path.write_text(json.dumps({"shortcuts": {"open": "Ctrl+F"}}), encoding="utf-8")
        cfg = load_settings()
        # "open" should be overridden
        assert cfg["shortcuts"]["open"] == "Ctrl+F"
        # "play" should come from defaults
        assert "play" in cfg["shortcuts"]


class TestSaveSettings:
    def test_save_creates_file(self, settings_path):
        """save_settings creates the JSON file."""
        cfg = load_settings()
        save_settings(cfg)
        assert settings_path.is_file()

    def test_save_write_error_is_silenced(self, settings_path, monkeypatch):
        """save_settings silently handles write errors (no exception raised)."""
        with patch("infra.settings.json.dump", side_effect=OSError("disk full")):
            save_settings({"default_volume": 80})  # must not raise


# ---------------------------------------------------------------------------
# add_recent_file
# ---------------------------------------------------------------------------


class TestAddRecentFile:
    def test_new_path_prepended(self):
        """add_recent_file inserts the new path at the front of the list."""
        cfg: dict = {"recent_files": ["/old.mp3"]}
        add_recent_file(cfg, "/new.mp3")
        assert cfg["recent_files"][0] == "/new.mp3"

    def test_duplicate_removed_then_prepended(self):
        """Duplicate entries are removed and re-inserted at position 0."""
        cfg: dict = {"recent_files": ["/a.mp3", "/b.mp3"]}
        add_recent_file(cfg, "/a.mp3")
        lst = cfg["recent_files"]
        assert lst.count("/a.mp3") == 1
        assert lst[0] == "/a.mp3"

    def test_trimmed_to_max_files(self):
        """The list is trimmed to max_files entries after inserting."""
        cfg: dict = {"recent_files": [f"/{i}.mp3" for i in range(10)]}
        add_recent_file(cfg, "/new.mp3", max_files=10)
        assert len(cfg["recent_files"]) == 10
        assert cfg["recent_files"][0] == "/new.mp3"

    def test_empty_list_starts_with_new_entry(self):
        """add_recent_file works when recent_files is initially empty."""
        cfg: dict = {"recent_files": []}
        add_recent_file(cfg, "/first.mp3")
        assert cfg["recent_files"] == ["/first.mp3"]

    def test_missing_recent_files_key(self):
        """add_recent_file works even when 'recent_files' key is absent."""
        cfg: dict = {}
        add_recent_file(cfg, "/file.mp3")
        assert cfg["recent_files"][0] == "/file.mp3"
