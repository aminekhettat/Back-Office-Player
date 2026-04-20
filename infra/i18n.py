"""
Internationalisation (i18n) module.

Provides a lightweight translation engine for Back-Office Player.
Supported languages: French (``"fr"``) and English (``"en"``).

The active language is determined at start-up from the OS locale and
can be overridden at any time via :func:`set_language`.  All UI widgets
should call :func:`tr` to obtain their display strings, and expose a
``retranslate_ui()`` method that re-applies translations when the
language is switched at runtime.

Usage example::

    from infra.i18n import tr, set_language
    label.setText(tr("play"))
    set_language("en")

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2026-04-19
:version: 1.1.4
:disclaimer: Distributed on an "AS IS" basis, WITHOUT WARRANTIES OR
             CONDITIONS OF ANY KIND. See the LICENSE file for the full
             terms of the Apache License, Version 2.0.
:version: 1.1.4
"""

from __future__ import annotations

import locale
import logging

_logger = logging.getLogger(__name__)

# ── Translation table ──────────────────────────────────────────────────────
# Each entry is  key → {"fr": French text, "en": English text}.
# Keys are short, stable identifiers; never user-visible.

_TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Window / application ─────────────────────────────────────────────
    "app_title": {
        "fr": "Back-Office Player",
        "en": "Back-Office Player",
    },
    # ── Menus ────────────────────────────────────────────────────────────
    "menu_file": {"fr": "&Fichier", "en": "&File"},
    "menu_open": {"fr": "&Ouvrir…", "en": "&Open…"},
    "menu_recent": {"fr": "Fichiers récents", "en": "Recent Files"},
    "menu_recent_none": {"fr": "(aucun)", "en": "(none)"},
    "menu_export_csv": {
        "fr": "Exporter les segments en &CSV…",
        "en": "Export segments as &CSV…",
    },
    "menu_quit": {"fr": "&Quitter", "en": "&Quit"},
    "menu_settings": {"fr": "&Paramètres", "en": "&Settings"},
    "menu_prefs": {"fr": "&Préférences…", "en": "&Preferences…"},
    "menu_history": {
        "fr": "&Historique de pratique…",
        "en": "Practice &History…",
    },
    "menu_language": {"fr": "&Langue", "en": "&Language"},
    "menu_lang_fr": {"fr": "Français", "en": "Français"},
    "menu_lang_en": {"fr": "English", "en": "English"},
    "menu_edit": {"fr": "&Édition", "en": "&Edit"},
    "menu_undo": {"fr": "&Annuler", "en": "&Undo"},
    "menu_redo": {"fr": "&Rétablir", "en": "&Redo"},
    "menu_playback": {"fr": "&Lecture", "en": "&Playback"},
    "menu_play_pause": {"fr": "Lecture / Pause", "en": "Play / Pause"},
    "menu_stop": {"fr": "Arrêt", "en": "Stop"},
    "menu_set_a": {"fr": "Définir point &A", "en": "Set point &A"},
    "menu_set_b": {"fr": "Définir point &B", "en": "Set point &B"},
    "menu_clear_ab": {"fr": "Effacer A/B", "en": "Clear A/B"},
    "menu_toggle_loop": {"fr": "Activer/désactiver la boucle", "en": "Toggle loop"},
    "menu_save_segment": {"fr": "Sauvegarder le segment", "en": "Save segment"},
    "menu_next_segment": {"fr": "Segment &suivant", "en": "&Next segment"},
    "menu_prev_segment": {"fr": "Segment &précédent", "en": "&Previous segment"},
    "menu_export_bop": {"fr": "&Exporter la configuration (.bop)…", "en": "&Export config (.bop)…"},
    "menu_import_bop": {
        "fr": "&Importer une configuration (.bop)…",
        "en": "&Import config (.bop)…",
    },
    "menu_help": {"fr": "&Aide", "en": "&Help"},
    "menu_about": {"fr": "À &propos…", "en": "&About…"},
    "dlg_about_title": {"fr": "À propos de Back-Office Player", "en": "About Back-Office Player"},
    "chk_pitch_preserving_main": {
        "fr": "Préserver la tonalité lors du changement de tempo",
        "en": "Preserve pitch when changing tempo",
    },
    # ── Buttons ──────────────────────────────────────────────────────────
    "btn_play": {"fr": "Lecture", "en": "Play"},
    "btn_pause": {"fr": "Pause", "en": "Pause"},
    "btn_stop": {"fr": "Arrêt", "en": "Stop"},
    "btn_open": {"fr": "Ouvrir un fichier audio…", "en": "Open audio file…"},
    "btn_set_a": {"fr": "Déf. A", "en": "Set A"},
    "btn_set_b": {"fr": "Déf. B", "en": "Set B"},
    "btn_clear_ab": {"fr": "Effacer A/B", "en": "Clear A/B"},
    "btn_save_segment": {"fr": "Sauver segment", "en": "Save Segment"},
    "btn_export_config": {"fr": "Exporter config", "en": "Export Config"},
    "btn_import_config": {"fr": "Importer config", "en": "Import Config"},
    "btn_jump": {"fr": "Aller au segment", "en": "Jump to Segment"},
    "btn_delete_segment": {"fr": "Supprimer le segment", "en": "Delete Segment"},
    "btn_move_up": {"fr": "Monter", "en": "Move Up"},
    "btn_move_down": {"fr": "Descendre", "en": "Move Down"},
    "btn_export_wav": {"fr": "Exporter WAV", "en": "Export WAV"},
    "btn_export_csv_hist": {"fr": "Exporter CSV…", "en": "Export CSV…"},
    "btn_export_mp3": {"fr": "Exporter MP3", "en": "Export MP3"},
    # ── Labels ───────────────────────────────────────────────────────────
    "lbl_volume": {"fr": "Volume :", "en": "Volume:"},
    "lbl_position": {"fr": "Position :", "en": "Position:"},
    "lbl_tempo": {"fr": "Tempo :", "en": "Tempo:"},
    "lbl_pitch": {"fr": "Tonalité (demi-tons) :", "en": "Pitch (semitones):"},
    "lbl_no_file": {"fr": "Aucun fichier.", "en": "No file."},
    "lbl_no_file_loaded": {
        "fr": "Aucun fichier chargé.",
        "en": "No file loaded.",
    },
    "lbl_loop": {"fr": "Boucle A–B", "en": "A–B Loop"},
    "lbl_segments": {"fr": "Segments :", "en": "Segments:"},
    "lbl_category": {"fr": "Catégorie :", "en": "Category:"},
    "lbl_session_time": {"fr": "Temps de session :", "en": "Session time:"},
    "lbl_loop_count": {
        "fr": "Nombre de boucles (0 = infini) :",
        "en": "Loop count (0 = infinite):",
    },
    "lbl_loop_delay": {
        "fr": "Délai entre les boucles (s) :",
        "en": "Delay between loops (s):",
    },
    "lbl_prog_tempo": {"fr": "Tempo progressif", "en": "Progressive tempo"},
    "lbl_prog_start": {"fr": "Départ :", "en": "Start:"},
    "lbl_prog_step": {"fr": "Pas :", "en": "Step:"},
    "lbl_prog_target": {"fr": "Cible :", "en": "Target:"},
    # ── Status messages ───────────────────────────────────────────────────
    "status_load_error": {
        "fr": "Erreur de chargement.",
        "en": "Load error.",
    },
    "status_playing": {"fr": "Lecture en cours.", "en": "Playing."},
    "status_paused": {"fr": "Pause.", "en": "Paused."},
    "status_stopped": {"fr": "Arrêté.", "en": "Stopped."},
    "status_loading": {"fr": "Chargement de {name}…", "en": "Loading {name}…"},
    "status_loaded": {
        "fr": "Fichier chargé : {name}",
        "en": "File loaded: {name}",
    },
    "status_point_a": {
        "fr": "Point A défini à {time}.",
        "en": "Point A set at {time}.",
    },
    "status_point_b": {
        "fr": "Point B défini à {time}.",
        "en": "Point B set at {time}.",
    },
    "status_ab_cleared": {
        "fr": "Points A et B effacés, boucle désactivée.",
        "en": "Points A and B cleared, loop disabled.",
    },
    "status_segment_jumped": {
        "fr": "Segment « {name} » ({start} – {end}) — A/B définis.",
        "en": "Jumped to segment '{name}' ({start} – {end}) — A/B set.",
    },
    "status_no_next": {
        "fr": "Aucun segment suivant.",
        "en": "No next segment.",
    },
    "status_no_prev": {
        "fr": "Aucun segment précédent.",
        "en": "No previous segment.",
    },
    "status_segment_saved": {
        "fr": "Segment « {name} » sauvegardé ({start} – {end}).",
        "en": "Segment '{name}' saved ({start} – {end}).",
    },
    "status_config_exported": {
        "fr": "Configuration exportée vers {path}.",
        "en": "Configuration exported to {path}.",
    },
    "status_config_imported": {
        "fr": "Configuration importée ({count} segments).",
        "en": "Configuration imported ({count} segments).",
    },
    "status_segments_exported": {
        "fr": "Segments exportés vers {path}.",
        "en": "Segments exported to {path}.",
    },
    "status_wav_exported": {
        "fr": "Segment « {name} » exporté en WAV.",
        "en": "Segment '{name}' exported as WAV.",
    },
    "status_session_done": {
        "fr": "Session terminée — {count} boucles.",
        "en": "Session complete — {count} loops.",
    },
    "status_undo": {"fr": "Annulation effectuée.", "en": "Undo performed."},
    "status_nothing_undo": {
        "fr": "Rien à annuler.",
        "en": "Nothing to undo.",
    },
    "status_redo": {
        "fr": "Rétablissement effectué.",
        "en": "Redo performed.",
    },
    "status_nothing_redo": {
        "fr": "Rien à rétablir.",
        "en": "Nothing to redo.",
    },
    "status_update": {
        "fr": "Mise à jour disponible : {version} — rendez-vous sur GitHub pour télécharger.",
        "en": "Update available: {version} — visit GitHub to download.",
    },
    # ── Dialogs ────────────────────────────────────────────────────────────
    "dlg_file_not_found_title": {
        "fr": "Fichier introuvable",
        "en": "File Not Found",
    },
    "dlg_file_not_found_msg": {
        "fr": "Le fichier suivant est introuvable :\n{path}",
        "en": "The following file could not be found:\n{path}",
    },
    "dlg_invalid_ab_title": {
        "fr": "Points A/B invalides",
        "en": "Invalid A-B Points",
    },
    "dlg_invalid_ab_msg": {
        "fr": "Veuillez définir des points A et B valides (B doit être après A).",
        "en": "Please set valid A and B points (B must be after A).",
    },
    "dlg_save_segment_title": {
        "fr": "Sauvegarder le segment",
        "en": "Save Segment",
    },
    "dlg_save_segment_label": {
        "fr": "Nom du segment :",
        "en": "Segment name:",
    },
    "dlg_export_config_title": {
        "fr": "Exporter la configuration de pratique",
        "en": "Export Practice Configuration",
    },
    "dlg_import_config_title": {
        "fr": "Importer la configuration de pratique",
        "en": "Import Practice Configuration",
    },
    "dlg_export_csv_title": {
        "fr": "Exporter les segments en CSV",
        "en": "Export Segments as CSV",
    },
    "dlg_export_wav_title": {
        "fr": "Exporter le segment en WAV",
        "en": "Export Segment as WAV",
    },
    "dlg_export_mp3_title": {
        "fr": "Exporter le segment en MP3",
        "en": "Export Segment as MP3",
    },
    "dlg_err_export_mp3": {
        "fr": "Impossible d'exporter le segment en MP3 : {err}",
        "en": "Could not export segment as MP3: {err}",
    },
    "status_mp3_exported": {
        "fr": "Segment « {name} » exporté en MP3.",
        "en": "Segment '{name}' exported as MP3.",
    },
    "dlg_exported_title": {"fr": "Exporté", "en": "Exported"},
    "dlg_imported_title": {"fr": "Importé", "en": "Imported"},
    "dlg_deleted_title": {"fr": "Supprimé", "en": "Deleted"},
    "dlg_error_title": {"fr": "Erreur", "en": "Error"},
    "dlg_open_audio_title": {
        "fr": "Choisir un fichier audio",
        "en": "Open Audio File",
    },
    "dlg_config_saved": {
        "fr": "Configuration sauvegardée dans {path}",
        "en": "Configuration saved to {path}",
    },
    "dlg_config_loaded": {
        "fr": "Configuration chargée depuis {path}",
        "en": "Configuration loaded from {path}",
    },
    "dlg_segments_exported": {
        "fr": "Segments exportés vers {path}",
        "en": "Segments exported to {path}",
    },
    "dlg_segment_deleted": {
        "fr": "Segment « {name} » supprimé.",
        "en": "Segment '{name}' deleted.",
    },
    "dlg_wav_exported": {
        "fr": "Segment « {name} » exporté vers {path}",
        "en": "Segment '{name}' exported to {path}",
    },
    "dlg_no_selection_title": {
        "fr": "Aucune sélection",
        "en": "No Selection",
    },
    "dlg_no_selection_msg": {
        "fr": "Veuillez sélectionner un segment à supprimer.",
        "en": "Please select a segment to delete.",
    },
    "dlg_no_selection_export_msg": {
        "fr": "Veuillez sélectionner un segment à exporter.",
        "en": "Please select a segment to export.",
    },
    "dlg_err_export_config": {
        "fr": "Impossible d'exporter la configuration : {err}",
        "en": "Could not export configuration: {err}",
    },
    "dlg_err_import_config": {
        "fr": "Impossible d'importer la configuration : {err}",
        "en": "Could not import configuration: {err}",
    },
    "dlg_err_export_segments": {
        "fr": "Impossible d'exporter les segments : {err}",
        "en": "Could not export segments: {err}",
    },
    "dlg_err_export_wav": {
        "fr": "Impossible d'exporter le segment : {err}",
        "en": "Could not export segment: {err}",
    },
    # ── File filter strings ───────────────────────────────────────────────
    "filter_audio": {
        "fr": "Fichiers audio (*.mp3 *.wav *.wma *.flac *.ogg);;Tous les fichiers (*.*)",
        "en": "Audio files (*.mp3 *.wav *.wma *.flac *.ogg);;All files (*.*)",
    },
    "filter_bop": {
        "fr": "Fichiers BOP (*.bop);;Tous les fichiers (*.*)",
        "en": "BOP Files (*.bop);;All files (*.*)",
    },
    "filter_csv": {
        "fr": "Fichiers CSV (*.csv);;Fichiers texte (*.txt);;Tous les fichiers (*.*)",
        "en": "CSV Files (*.csv);;Text Files (*.txt);;All files (*.*)",
    },
    "filter_wav": {
        "fr": "Fichiers WAV (*.wav);;Tous les fichiers (*.*)",
        "en": "WAV Files (*.wav);;All files (*.*)",
    },
    "filter_mp3": {
        "fr": "Fichiers MP3 (*.mp3);;Tous les fichiers (*.*)",
        "en": "MP3 Files (*.mp3);;All files (*.*)",
    },
    # ── Settings dialog ───────────────────────────────────────────────────
    "settings_title": {"fr": "Préférences", "en": "Preferences"},
    "settings_accessible_desc": {
        "fr": "Personnalisez les raccourcis clavier et l'apparence de l'application.",
        "en": "Customise keyboard shortcuts and application appearance.",
    },
    "settings_tabs_accessible_name": {
        "fr": "Onglets des paramètres",
        "en": "Settings tabs",
    },
    "settings_tab_shortcuts": {"fr": "Raccourcis", "en": "Shortcuts"},
    "settings_tab_shortcuts_accessible_name": {
        "fr": "Onglet Raccourcis",
        "en": "Shortcuts tab",
    },
    "settings_tab_appearance": {"fr": "Apparence", "en": "Appearance"},
    "settings_tab_appearance_accessible_name": {
        "fr": "Onglet Apparence",
        "en": "Appearance tab",
    },
    "settings_theme_group": {"fr": "Thème", "en": "Theme"},
    "settings_theme_group_accessible_name": {
        "fr": "Groupe thème",
        "en": "Theme group",
    },
    "settings_theme_label": {
        "fr": "Thème de couleurs :",
        "en": "Colour theme:",
    },
    "settings_theme_combo_accessible_name": {
        "fr": "Sélecteur de thème",
        "en": "Theme selector",
    },
    "settings_theme_combo_accessible_desc": {
        "fr": "Choisissez le thème de couleurs de l'application.",
        "en": "Choose the application colour theme.",
    },
    "settings_accessibility_group": {
        "fr": "Accessibilité",
        "en": "Accessibility",
    },
    "settings_accessibility_group_accessible_name": {
        "fr": "Groupe accessibilité",
        "en": "Accessibility group",
    },
    "settings_announce_label": {
        "fr": "Intervalle d'annonce de position :",
        "en": "Position announce interval:",
    },
    "settings_announce_spin_accessible_name": {
        "fr": "Intervalle d'annonce de position",
        "en": "Position announce interval",
    },
    "settings_announce_spin_accessible_desc": {
        "fr": (
            "Fréquence (en secondes) à laquelle la position de lecture "
            "est annoncée aux lecteurs d'écran."
        ),
        "en": (
            "Frequency (in seconds) at which the playback position "
            "is announced to screen readers."
        ),
    },
    "settings_audio_group": {
        "fr": "Traitement audio",
        "en": "Audio Processing",
    },
    "settings_audio_group_accessible_name": {
        "fr": "Groupe traitement audio",
        "en": "Audio processing group",
    },
    "settings_pitch_preserving": {
        "fr": "Tempo sans modification de la hauteur",
        "en": "Pitch-preserving tempo",
    },
    "settings_pitch_preserving_accessible_name": {
        "fr": "Case à cocher tempo sans modification de la hauteur",
        "en": "Pitch-preserving tempo checkbox",
    },
    "settings_pitch_preserving_accessible_desc": {
        "fr": (
            "Si activé, modifier le tempo ne change pas la hauteur tonale "
            "(étirement temporel). Nécessite un temps de traitement avant la lecture."
        ),
        "en": (
            "When enabled, changing the tempo does not alter the pitch "
            "(time-stretching). Requires processing time before playback."
        ),
    },
    # ── Settings dialog — shortcut labels ────────────────────────────────
    "shortcut_open": {
        "fr": "Ouvrir un fichier (Ctrl+O)",
        "en": "Open file (Ctrl+O)",
    },
    "shortcut_play": {
        "fr": "Lecture (Ctrl+P)",
        "en": "Play (Ctrl+P)",
    },
    "shortcut_pause": {
        "fr": "Pause (Ctrl+Maj+P)",
        "en": "Pause (Ctrl+Shift+P)",
    },
    "shortcut_stop": {
        "fr": "Arrêt (Ctrl+S)",
        "en": "Stop (Ctrl+S)",
    },
    "shortcut_set_a": {
        "fr": "Définir le point A (Ctrl+Maj+A)",
        "en": "Set point A (Ctrl+Shift+A)",
    },
    "shortcut_set_b": {
        "fr": "Définir le point B (Ctrl+Maj+B)",
        "en": "Set point B (Ctrl+Shift+B)",
    },
    "shortcut_save_segment": {
        "fr": "Sauvegarder le segment (Ctrl+Maj+S)",
        "en": "Save segment (Ctrl+Shift+S)",
    },
    "shortcut_export_config": {
        "fr": "Exporter la config (Ctrl+E)",
        "en": "Export config (Ctrl+E)",
    },
    "shortcut_import_config": {
        "fr": "Importer la config (Ctrl+I)",
        "en": "Import config (Ctrl+I)",
    },
    "shortcut_next_segment": {
        "fr": "Segment suivant (Ctrl+Droite)",
        "en": "Next segment (Ctrl+Right)",
    },
    "shortcut_prev_segment": {
        "fr": "Segment précédent (Ctrl+Gauche)",
        "en": "Previous segment (Ctrl+Left)",
    },
    # ── Segment list widget ───────────────────────────────────────────────
    "segment_list_accessible_name": {
        "fr": "Liste des segments",
        "en": "Segment list",
    },
    "segment_list_accessible_desc": {
        "fr": (
            "Liste de tous les segments nommés pour le fichier audio courant. "
            "Sélectionnez un segment et appuyez sur Entrée ou cliquez sur "
            "« Aller au segment » pour y naviguer."
        ),
        "en": (
            "List of all named segments for the current audio file. "
            "Select a segment and press Enter or click 'Jump to Segment' to navigate."
        ),
    },
    "segment_list_label": {"fr": "Segments :", "en": "Segments:"},
    "segment_list_category_label": {"fr": "Catégorie :", "en": "Category:"},
    "segment_list_category_filter_accessible_name": {
        "fr": "Filtre de catégorie",
        "en": "Category filter",
    },
    "segment_list_category_filter_accessible_desc": {
        "fr": (
            "Filtrer la liste des segments par catégorie. "
            "Sélectionnez « (toutes) » pour afficher tous les segments."
        ),
        "en": ("Filter the segment list by category. " "Select '(all)' to show all segments."),
    },
    "segment_list_all_categories": {"fr": "(toutes)", "en": "(all)"},
    "segment_btn_jump_accessible_name": {
        "fr": "Aller au segment sélectionné",
        "en": "Jump to selected segment",
    },
    "segment_btn_jump_accessible_desc": {
        "fr": "Déplacer la lecture au début du segment sélectionné.",
        "en": "Move playback to the start of the selected segment.",
    },
    "segment_btn_delete_accessible_name": {
        "fr": "Supprimer le segment sélectionné",
        "en": "Delete selected segment",
    },
    "segment_btn_delete_accessible_desc": {
        "fr": "Retirer le segment sélectionné de la liste.",
        "en": "Remove the selected segment from the list.",
    },
    "segment_btn_move_up_accessible_name": {
        "fr": "Monter le segment",
        "en": "Move segment up",
    },
    "segment_btn_move_up_accessible_desc": {
        "fr": "Déplacer le segment sélectionné d'une position vers le haut.",
        "en": "Move the selected segment one position up.",
    },
    "segment_btn_move_down_accessible_name": {
        "fr": "Descendre le segment",
        "en": "Move segment down",
    },
    "segment_btn_move_down_accessible_desc": {
        "fr": "Déplacer le segment sélectionné d'une position vers le bas.",
        "en": "Move the selected segment one position down.",
    },
    "segment_btn_export_wav_accessible_name": {
        "fr": "Exporter le segment en WAV",
        "en": "Export segment as WAV",
    },
    "segment_btn_export_wav_accessible_desc": {
        "fr": "Exporter le segment sélectionné sous forme de fichier WAV 16 bits.",
        "en": "Export the selected segment as a 16-bit WAV file.",
    },
    "segment_btn_export_mp3_accessible_name": {
        "fr": "Exporter le segment en MP3",
        "en": "Export segment as MP3",
    },
    "segment_btn_export_mp3_accessible_desc": {
        "fr": "Exporter le segment sélectionné sous forme de fichier MP3.",
        "en": "Export the selected segment as an MP3 file.",
    },
    "dlg_no_selection_export_mp3_msg": {
        "fr": "Veuillez sélectionner un segment à exporter en MP3.",
        "en": "Please select a segment to export as MP3.",
    },
    "dlg_no_selection_delete_msg": {
        "fr": "Veuillez sélectionner un segment à supprimer.",
        "en": "Please select a segment to delete.",
    },
    "dlg_no_selection_export_wav_msg": {
        "fr": "Veuillez sélectionner un segment à exporter.",
        "en": "Please select a segment to export.",
    },
    # ── History dialog ────────────────────────────────────────────────────
    "history_title": {
        "fr": "Historique de pratique",
        "en": "Practice History",
    },
    "history_accessible_desc": {
        "fr": "Tableau de toutes les sessions de pratique enregistrées.",
        "en": "Table of all recorded practice sessions.",
    },
    "history_summary_label": {
        "fr": "Résumé de l'historique",
        "en": "History summary",
    },
    "history_table_accessible_name": {
        "fr": "Tableau de l'historique de pratique",
        "en": "Practice history table",
    },
    "history_table_accessible_desc": {
        "fr": (
            "Chaque ligne représente une session de pratique. "
            "Colonnes : date/heure, fichier, durée, boucles, tempo moyen, notes."
        ),
        "en": (
            "Each row represents one practice session. "
            "Columns: date/time, file, duration, loops, average tempo, notes."
        ),
    },
    "history_btn_export_accessible_name": {
        "fr": "Exporter l'historique en CSV",
        "en": "Export history as CSV",
    },
    "history_btn_export_accessible_desc": {
        "fr": "Enregistrer l'historique de pratique dans un fichier CSV.",
        "en": "Save the practice history to a CSV file.",
    },
    "history_col_date": {"fr": "Date / Heure", "en": "Date / Time"},
    "history_col_file": {"fr": "Fichier audio", "en": "Audio File"},
    "history_col_duration": {"fr": "Durée (s)", "en": "Duration (s)"},
    "history_col_loops": {"fr": "Boucles", "en": "Loops"},
    "history_col_tempo": {"fr": "Tempo moy.", "en": "Avg Tempo"},
    "history_col_notes": {"fr": "Notes", "en": "Notes"},
    "history_summary": {
        "fr": "{n} session(s) — {loops} boucles au total — durée cumulée : {dur}",
        "en": "{n} session(s) — {loops} loops total — cumulative time: {dur}",
    },
    "history_export_title": {
        "fr": "Exporter l'historique en CSV",
        "en": "Export History as CSV",
    },
    "history_export_default": {
        "fr": "historique_pratique.csv",
        "en": "practice_history.csv",
    },
    "history_exported": {
        "fr": "Historique exporté vers {path}",
        "en": "History exported to {path}",
    },
    "history_err_export": {
        "fr": "Impossible d'exporter l'historique : {err}",
        "en": "Could not export history: {err}",
    },
    # ── Practice panel ────────────────────────────────────────────────────
    "practice_panel_title": {
        "fr": "Session de pratique",
        "en": "Practice Session",
    },
    # ── Language change ───────────────────────────────────────────────────
    "lang_changed_title": {
        "fr": "Langue modifiée",
        "en": "Language Changed",
    },
    "lang_changed_msg": {
        "fr": "La langue a été changée en Français.",
        "en": "The language has been changed to English.",
    },
}

# ── Module-level state ────────────────────────────────────────────────────

_CURRENT_LANG: str = "fr"
_SUPPORTED = frozenset({"fr", "en"})


def _detect_system_language() -> str:
    """
    Return ``"fr"`` if the OS locale is French, otherwise ``"en"``.

    Uses :func:`locale.getlocale` (which honours ``LANG``/``LC_ALL``
    environment variables on POSIX systems).
    """
    try:
        lang_code, _ = locale.getlocale()
        if lang_code and lang_code.lower().startswith("fr"):
            return "fr"
    except Exception as exc:
        _logger.warning("Could not detect system language: %s", exc)
    return "en"


def init_language(stored_lang: str | None = None) -> None:
    """
    Initialise the active language.

    Priority order:

    1. *stored_lang* from ``settings.json`` (if valid).
    2. OS system locale (French ↔ English detection).

    Parameters
    ----------
    stored_lang : str or None
        Language code previously stored by the user (``"fr"`` or ``"en"``).
        Pass ``None`` to fall back to OS detection.
    """
    global _CURRENT_LANG
    if stored_lang in _SUPPORTED:
        _CURRENT_LANG = stored_lang
    else:
        _CURRENT_LANG = _detect_system_language()


def set_language(lang: str) -> None:
    """
    Set the active language at runtime.

    Parameters
    ----------
    lang : str
        Language code — ``"fr"`` or ``"en"``.

    Raises
    ------
    ValueError
        If *lang* is not a supported language code.
    """
    global _CURRENT_LANG
    if lang not in _SUPPORTED:
        raise ValueError(
            f"Langue non supportée : {lang!r}. " f"Valeurs acceptées : {sorted(_SUPPORTED)}"
        )
    _CURRENT_LANG = lang


def get_language() -> str:
    """Return the currently active language code (``"fr"`` or ``"en"``)."""
    return _CURRENT_LANG


def tr(key: str, **kwargs: object) -> str:
    """
    Translate *key* to the currently active language.

    Optional keyword arguments are interpolated into the translated string
    using :meth:`str.format`.

    Parameters
    ----------
    key : str
        Translation key (must exist in :data:`_TRANSLATIONS`).
    **kwargs :
        Named placeholders referenced in the translated string
        (e.g. ``tr("status_loaded", name="song.mp3")``).

    Returns
    -------
    str
        Translated string, with placeholders resolved.

    Raises
    ------
    KeyError
        If *key* is not found in the translation table.
    """
    entry = _TRANSLATIONS[key]  # raises KeyError if unknown key
    text = entry.get(_CURRENT_LANG, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
