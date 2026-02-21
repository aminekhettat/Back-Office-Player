Audio Player Native Module
===========================

.. automodule:: core.audio_player_native
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The `audio_player_native` module provides a cross-platform audio playback engine
without external dependencies like VLC. It uses:

- **librosa** for audio file loading (supports MP3, WAV, FLAC, OGG, WMA, etc.)
- **sounddevice** for hardware playback
- **numpy** for audio array processing

Key Features
~~~~~~~~~~~~

- **Format Support**: All formats supported by librosa (MP3, WAV, FLAC, OGG, WMA, AIFF, etc.)
- **Position Control**: Precise seeking in seconds
- **Volume Control**: 0-100 scale
- **Tempo Control**: 0.5x – 2.0x playback speed (NEW in Phase 1)
- **Thread-Safe**: All operations protected by locks for multi-threaded safety
- **Efficient**: Uses numpy arrays for fast audio processing

Audio Player Class
------------------

.. autoclass:: core.audio_player_native.AudioPlayer
   :members:
   :private-members:
   :special-members: __init__
   :show-inheritance:

Example Usage
~~~~~~~~~~~~~

.. code-block:: python

    from core.audio_player_native import AudioPlayer

    # Initialize player
    player = AudioPlayer()

    # Load an audio file
    player.load_file("song.mp3")

    # Basic playback
    player.play()                    # Start playback
    player.set_volume(80)            # Set volume to 80%
    player.set_tempo(1.5)            # Playback at 1.5x speed
    player.pause()                   # Pause playback
    player.stop()                    # Stop and reset position

    # Seek in the track
    player.set_position(30.5)        # Jump to 30.5 seconds
    current_pos = player.get_position()
    duration = player.get_duration()

Differences from Original (VLC-based)
--------------------------------------

The new native player (`audio_player_native.py`) replaces the VLC-based player (`audio_player.py`):

- **No VLC Dependency**: Windows users no longer need to install VLC separately
- **Better Compatibility**: Works out-of-the-box on Windows, macOS, Linux
- **Native Playback**: Uses OS audio stack (WASAPI on Windows, CoreAudio on macOS, ALSA on Linux)
- **Tempo Control**: Added support for playback speed adjustment (0.5x – 2.0x)
- **Streaming**: More efficient memory usage with numpy-based playback

API Compatibility
~~~~~~~~~~~~~~~~~

The new player maintains API compatibility with the original:

- `load_file(path)` — Load an audio file
- `play()` — Start/resume playback
- `pause()` — Pause playback
- `stop()` — Stop and reset position
- `set_position(seconds)` — Seek to a position
- `get_position()` — Get current position
- `get_duration()` — Get total duration
- `set_volume(volume)` — Set volume (0-100)
- `get_volume()` — Get current volume
- **NEW**: `set_tempo(factor)` — Set playback speed (0.5 – 2.0)
- **NEW**: `get_tempo()` — Get current tempo factor

Implementation Details
~~~~~~~~~~~~~~~~~~~~~~

**Playback Architecture**

The player uses a background thread for audio streaming:

1. Audio is loaded via librosa (mono, normalized)
2. A sounddevice OutputStream is created
3. A playback worker thread feeds audio blocks to the stream
4. Position is tracked using system time and tempo factor
5. Thread safety is maintained via a reentrant lock

**Tempo Implementation**

Tempo changes are achieved by:

- Adjusting the playback start time reference
- Calculating position as: `elapsed_time × tempo_factor`
- No actual audio resampling (simple time-stretching)

Dependencies
~~~~~~~~~~~~

- **librosa** >= 0.10.0
- **sounddevice** >= 0.4.5
- **numpy** >= 1.20.0
- **scipy** >= 1.7.0 (required by librosa)

See Also
~~~~~~~~

- :mod:`core.segment_manager` — Manage named audio segments
- :mod:`ui.main_window` — Qt-based user interface
