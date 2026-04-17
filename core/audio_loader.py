"""
Asynchronous audio loader.

Provides a QThread that loads an audio file in the background so that
the GUI remains responsive during decoding.

:author: Amine Khettat
:organization: BLIND SYSTEMS
:copyright: (c) 2025 BLIND SYSTEMS
:license: Apache-2.0
:version: 1.1.2
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.audio_player_native import AudioPlayer


class AudioLoaderThread(QThread):
    """
    Thread de chargement audio.

    Charge un fichier audio dans un thread séparé via
    :meth:`~core.audio_player_native.AudioPlayer.load_file` afin de ne pas
    bloquer le thread Qt principal.

    Signaux
    -------
    loaded :
        Émis quand le fichier est chargé avec succès.
    error(str) :
        Émis si une erreur survient ; le message d'erreur est passé en argument.

    Paramètres
    ----------
    player : AudioPlayer
        Instance du lecteur audio dans laquelle charger le fichier.
    path : Path
        Chemin vers le fichier audio à charger.
    parent : QObject, optional
        Parent Qt.
    """

    loaded: Signal = Signal()
    error: Signal = Signal(str)

    def __init__(self, player: AudioPlayer, path: Path, parent=None) -> None:
        super().__init__(parent)
        self._player = player
        self._path = path

    def run(self) -> None:
        """Exécution dans le thread de chargement."""
        try:
            self._player.load_file(self._path)
            self.loaded.emit()
        except Exception as exc:
            self.error.emit(str(exc))
