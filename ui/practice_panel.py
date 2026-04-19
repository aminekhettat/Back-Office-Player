"""
PySide6 practice panel widget.

A QGroupBox that exposes loop count, progressive tempo, loop delay, and
a session timer to the user.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:date: 2026-04-19
:version: 1.1.3
:disclaimer: Distributed on an "AS IS" basis, WITHOUT WARRANTIES OR
             CONDITIONS OF ANY KIND. See the LICENSE file for the full
             terms of the Apache License, Version 2.0.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from core.practice_session import PracticeSession
from infra.i18n import tr


class PracticePanel(QGroupBox):
    """
    Control panel for structured practice sessions.

    Provides widgets to configure:

    - Session elapsed time display.
    - Loop count (0 = infinite).
    - Loop delay between repetitions.
    - Progressive tempo (optional tempo ramp).

    The panel maintains an internal :class:`~core.practice_session.PracticeSession`
    instance and a 1-second QTimer to refresh the elapsed-time label.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(tr("practice_panel_title"), parent)
        self.setAccessibleName("Panneau de session de pratique")
        self.setAccessibleDescription(
            "Configurez le nombre de boucles, le tempo progressif "
            "et visualisez le temps écoulé."
        )

        self._session: PracticeSession | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Session timer row ---
        timer_row = QHBoxLayout()
        lbl_timer_label = QLabel("Temps de session :")
        lbl_timer_label.setAccessibleName("Étiquette temps de session")
        self.lbl_session_time = QLabel("00:00:00")
        self.lbl_session_time.setAccessibleName("Temps écoulé de la session")
        self.lbl_session_time.setAccessibleDescription(
            "Temps écoulé depuis le début de la session de pratique."
        )
        timer_row.addWidget(lbl_timer_label)
        timer_row.addWidget(self.lbl_session_time)
        timer_row.addStretch()
        layout.addLayout(timer_row)

        # --- Loop count row ---
        loop_row = QHBoxLayout()
        lbl_loop = QLabel("Nombre de boucles (0 = infini) :")
        lbl_loop.setAccessibleName("Étiquette nombre de boucles")
        self.spn_loop_count = QSpinBox()
        self.spn_loop_count.setRange(0, 9999)
        self.spn_loop_count.setValue(0)
        self.spn_loop_count.setAccessibleName("Nombre de boucles")
        self.spn_loop_count.setAccessibleDescription(
            "Nombre de boucles A-B à effectuer. 0 signifie boucle infinie."
        )
        loop_row.addWidget(lbl_loop)
        loop_row.addWidget(self.spn_loop_count)
        loop_row.addStretch()
        layout.addLayout(loop_row)

        # --- Loop delay row ---
        delay_row = QHBoxLayout()
        lbl_delay = QLabel("Délai entre les boucles (s) :")
        lbl_delay.setAccessibleName("Étiquette délai de boucle")
        self.spn_loop_delay = QDoubleSpinBox()
        self.spn_loop_delay.setRange(0.0, 30.0)
        self.spn_loop_delay.setSingleStep(0.5)
        self.spn_loop_delay.setValue(0.0)
        self.spn_loop_delay.setAccessibleName("Délai de boucle")
        self.spn_loop_delay.setAccessibleDescription(
            "Secondes de pause entre les répétitions de la boucle A-B."
        )
        delay_row.addWidget(lbl_delay)
        delay_row.addWidget(self.spn_loop_delay)
        delay_row.addStretch()
        layout.addLayout(delay_row)

        # --- Progressive tempo ---
        self.chk_progressive = QCheckBox("Tempo progressif")
        self.chk_progressive.setAccessibleName("Case à cocher tempo progressif")
        self.chk_progressive.setAccessibleDescription(
            "Si coché, le tempo augmente d'un pas après chaque boucle."
        )
        self.chk_progressive.stateChanged.connect(self._on_progressive_changed)
        layout.addWidget(self.chk_progressive)

        # --- Progressive tempo parameters (hidden until enabled) ---
        self._progressive_widget_row = QHBoxLayout()

        lbl_start = QLabel("Départ :")
        lbl_start.setAccessibleName("Étiquette tempo de départ")
        self.spn_tempo_start = QDoubleSpinBox()
        self.spn_tempo_start.setRange(0.25, 2.0)
        self.spn_tempo_start.setSingleStep(0.05)
        self.spn_tempo_start.setValue(1.0)
        self.spn_tempo_start.setAccessibleName("Valeur tempo de départ")
        self.spn_tempo_start.setAccessibleDescription(
            "Facteur de tempo initial en mode progressif (ex. 0,75 = 75 %)."
        )

        lbl_step = QLabel("Pas :")
        lbl_step.setAccessibleName("Étiquette pas de tempo")
        self.spn_tempo_step = QDoubleSpinBox()
        self.spn_tempo_step.setRange(0.01, 0.5)
        self.spn_tempo_step.setSingleStep(0.01)
        self.spn_tempo_step.setValue(0.05)
        self.spn_tempo_step.setAccessibleName("Valeur pas de tempo")
        self.spn_tempo_step.setAccessibleDescription(
            "Quantité ajoutée au tempo après chaque boucle."
        )

        lbl_target = QLabel("Cible :")
        lbl_target.setAccessibleName("Étiquette tempo cible")
        self.spn_tempo_target = QDoubleSpinBox()
        self.spn_tempo_target.setRange(0.25, 2.0)
        self.spn_tempo_target.setSingleStep(0.05)
        self.spn_tempo_target.setValue(1.0)
        self.spn_tempo_target.setAccessibleName("Valeur tempo cible")
        self.spn_tempo_target.setAccessibleDescription(
            "Facteur de tempo maximal en mode progressif (ex. 1,0 = 100 %)."
        )

        self._progressive_widget_row.addWidget(lbl_start)
        self._progressive_widget_row.addWidget(self.spn_tempo_start)
        self._progressive_widget_row.addWidget(lbl_step)
        self._progressive_widget_row.addWidget(self.spn_tempo_step)
        self._progressive_widget_row.addWidget(lbl_target)
        self._progressive_widget_row.addWidget(self.spn_tempo_target)
        self._progressive_widget_row.addStretch()
        layout.addLayout(self._progressive_widget_row)

        # Hide progressive controls until checkbox is enabled
        self._set_progressive_widgets_visible(False)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_session(self) -> PracticeSession:
        """
        Build and return a :class:`~core.practice_session.PracticeSession`
        from the current widget values.

        The returned session is **not** started yet; call
        :meth:`start_session` to start it.
        """
        return PracticeSession(
            loop_count=self.spn_loop_count.value(),
            progressive_tempo=self.chk_progressive.isChecked(),
            tempo_start=self.spn_tempo_start.value(),
            tempo_step=self.spn_tempo_step.value(),
            tempo_target=self.spn_tempo_target.value(),
            loop_delay=self.spn_loop_delay.value(),
        )

    def start_session(self) -> PracticeSession:
        """
        Create, start, and return a new :class:`PracticeSession`.

        The internal 1-second timer is (re)started and the elapsed-time
        label is reset.
        """
        self._session = self.get_session()
        self._session.start()
        self.lbl_session_time.setText("00:00:00")
        self._timer.start()
        return self._session

    def stop_session(self) -> None:
        """Stop the active session and its display timer."""
        if self._session is not None:
            self._session.stop()
        self._timer.stop()

    def reset_session(self) -> None:
        """Stop the session and reset the elapsed-time label."""
        self.stop_session()
        self._session = None
        self.lbl_session_time.setText("00:00:00")

    def get_active_session(self) -> PracticeSession | None:
        """
        Return the active :class:`PracticeSession`, or ``None`` if no
        session is running.
        """
        if self._session is not None and self._session.is_active:
            return self._session
        return None

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        if self._session is not None:
            self.lbl_session_time.setText(self._session.get_elapsed())

    def _on_progressive_changed(self, state: int) -> None:
        self._set_progressive_widgets_visible(state != 0)

    def retranslate_ui(self) -> None:
        """Apply the current language to all translatable widgets."""
        self.setTitle(tr("practice_panel_title"))

    def _set_progressive_widgets_visible(self, visible: bool) -> None:
        for i in range(self._progressive_widget_row.count()):
            item = self._progressive_widget_row.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setVisible(visible)
