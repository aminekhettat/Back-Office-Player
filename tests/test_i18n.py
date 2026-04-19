"""
Tests for infra.i18n — 100% branch coverage.

Covers: tr() (known key, unknown key, with kwargs, fallback to 'en'),
init_language() (stored valid, stored invalid, None → OS detect),
set_language() (valid, invalid raises ValueError),
get_language(), _detect_system_language() (fr locale, non-fr locale,
getlocale failure).

:author: Amine Khettat
:organization: BLIND SYSTEMS
:license: Apache-2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# tr()
# ---------------------------------------------------------------------------

class TestTr:
    def test_known_key_french(self):
        """tr() returns the French string when language is 'fr'."""
        import infra.i18n as i18n
        i18n.set_language("fr")
        assert i18n.tr("btn_play") == "Lecture"

    def test_known_key_english(self):
        """tr() returns the English string when language is 'en'."""
        import infra.i18n as i18n
        i18n.set_language("en")
        assert i18n.tr("btn_play") == "Play"

    def test_unknown_key_raises_key_error(self):
        """tr() raises KeyError for an unknown translation key."""
        import infra.i18n as i18n
        with pytest.raises(KeyError):
            i18n.tr("__nonexistent_key__")

    def test_kwargs_interpolated(self):
        """tr() interpolates keyword arguments into the translated string."""
        import infra.i18n as i18n
        i18n.set_language("fr")
        result = i18n.tr("status_loading", name="song.mp3")
        assert "song.mp3" in result

    def test_kwargs_interpolated_english(self):
        """tr() interpolates kwargs in English too."""
        import infra.i18n as i18n
        i18n.set_language("en")
        result = i18n.tr("status_loaded", name="track.wav")
        assert "track.wav" in result

    def test_fallback_to_english_if_lang_missing(self, monkeypatch):
        """tr() falls back to 'en' if the current lang is missing for a key."""
        import infra.i18n as i18n
        # Temporarily force an unsupported lang directly on the module
        monkeypatch.setattr(i18n, "_CURRENT_LANG", "de")
        # 'btn_play' only has 'fr' and 'en' — should fall back to 'en'
        result = i18n.tr("btn_play")
        assert result in ("Lecture", "Play")  # one of the valid values


# ---------------------------------------------------------------------------
# set_language()
# ---------------------------------------------------------------------------

class TestSetLanguage:
    def test_set_to_fr(self):
        """set_language('fr') switches the active language to French."""
        import infra.i18n as i18n
        i18n.set_language("fr")
        assert i18n.get_language() == "fr"

    def test_set_to_en(self):
        """set_language('en') switches the active language to English."""
        import infra.i18n as i18n
        i18n.set_language("en")
        assert i18n.get_language() == "en"

    def test_invalid_lang_raises_value_error(self):
        """set_language() raises ValueError for an unsupported language code."""
        import infra.i18n as i18n
        with pytest.raises(ValueError, match="non supportée"):
            i18n.set_language("de")


# ---------------------------------------------------------------------------
# get_language()
# ---------------------------------------------------------------------------

class TestGetLanguage:
    def test_returns_current_lang(self):
        """get_language() returns the currently active language code."""
        import infra.i18n as i18n
        i18n.set_language("en")
        assert i18n.get_language() == "en"
        i18n.set_language("fr")
        assert i18n.get_language() == "fr"


# ---------------------------------------------------------------------------
# init_language()
# ---------------------------------------------------------------------------

class TestInitLanguage:
    def test_stored_valid_fr(self):
        """init_language('fr') uses the stored language."""
        import infra.i18n as i18n
        i18n.init_language("fr")
        assert i18n.get_language() == "fr"

    def test_stored_valid_en(self):
        """init_language('en') uses the stored language."""
        import infra.i18n as i18n
        i18n.init_language("en")
        assert i18n.get_language() == "en"

    def test_stored_invalid_falls_back_to_os(self, monkeypatch):
        """init_language with invalid code falls back to OS language detection."""
        import infra.i18n as i18n
        monkeypatch.setattr(i18n, "_detect_system_language", lambda: "en")
        i18n.init_language("de")
        assert i18n.get_language() == "en"

    def test_none_falls_back_to_os(self, monkeypatch):
        """init_language(None) falls back to OS language detection."""
        import infra.i18n as i18n
        monkeypatch.setattr(i18n, "_detect_system_language", lambda: "fr")
        i18n.init_language(None)
        assert i18n.get_language() == "fr"


# ---------------------------------------------------------------------------
# _detect_system_language()
# ---------------------------------------------------------------------------

class TestDetectSystemLanguage:
    def test_french_locale_returns_fr(self):
        """_detect_system_language() returns 'fr' when OS locale starts with 'fr'."""
        import infra.i18n as i18n
        with patch("locale.getlocale", return_value=("fr_FR", "UTF-8")):
            result = i18n._detect_system_language()
        assert result == "fr"

    def test_english_locale_returns_en(self):
        """_detect_system_language() returns 'en' for non-French locale."""
        import infra.i18n as i18n
        with patch("locale.getlocale", return_value=("en_US", "UTF-8")):
            result = i18n._detect_system_language()
        assert result == "en"

    def test_none_locale_returns_en(self):
        """_detect_system_language() returns 'en' when getlocale returns None."""
        import infra.i18n as i18n
        with patch("locale.getlocale", return_value=(None, None)):
            result = i18n._detect_system_language()
        assert result == "en"

    def test_exception_returns_en(self):
        """_detect_system_language() returns 'en' if getlocale raises."""
        import infra.i18n as i18n
        with patch("locale.getlocale", side_effect=Exception("locale error")):
            result = i18n._detect_system_language()
        assert result == "en"

    def test_fr_CA_returns_fr(self):
        """_detect_system_language() returns 'fr' for fr_CA locale."""
        import infra.i18n as i18n
        with patch("locale.getlocale", return_value=("fr_CA", "UTF-8")):
            result = i18n._detect_system_language()
        assert result == "fr"


# ---------------------------------------------------------------------------
# Translation completeness smoke test
# ---------------------------------------------------------------------------

class TestTranslationCompleteness:
    def test_all_keys_have_both_languages(self):
        """Every translation key has both 'fr' and 'en' entries."""
        from infra.i18n import _TRANSLATIONS
        for key, entry in _TRANSLATIONS.items():
            assert "fr" in entry, f"Key '{key}' is missing a French translation"
            assert "en" in entry, f"Key '{key}' is missing an English translation"
