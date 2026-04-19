.. _user_manual_en:

=============================================
Back-Office Player — User Manual (English)
=============================================

| **Version:** 2.0.0
| **Date:** April 19, 2026
| **Author:** Amine Khettat — BLIND SYSTEMS
| **Contact:** amine.khettat@blindsystems.org
| **License:** Apache-2.0

.. contents:: Table of Contents
   :depth: 3
   :local:


Introduction
============

**Back-Office Player (BOP)** is a free, accessible audio practice tool for
music students. It lets you open any audio recording (MP3, WAV, FLAC, …),
mark sections you want to work on, loop them at a reduced speed, and gradually
build up to full tempo — all without using a mouse, thanks to full keyboard
and screen-reader support.

BOP was developed by `BLIND SYSTEMS <https://www.blindsystems.org>`_ for the
students of the `Culture Musique / Saba Music <https://www.sabamusic.fr>`_
association.


System Requirements
===================

* **Operating system:** Windows 10 or Windows 11 (64-bit)
* **Internet connection:** only required for checking for updates (can be
  disabled in Preferences)
* No Python installation needed — the standalone ``BackOfficePlayer.exe``
  embeds everything


Installation
============

Standalone executable (recommended)
-------------------------------------

1. Download ``BackOfficePlayer-2.0.0-win64.zip`` from the
   `GitHub Releases page <https://github.com/aminekhettat/Back-Office-Player/releases>`_.
2. Extract the ZIP anywhere on your computer (e.g. ``C:\Programs\BOP\``).
3. Double-click ``BackOfficePlayer.exe`` to launch.
4. Windows SmartScreen may warn about an unknown publisher the first time.
   Click **More info → Run anyway**.

No installation, no registry entries, no administrator rights required.


Running from Source
--------------------

.. code-block:: bash

   git clone https://github.com/aminekhettat/Back-Office-Player.git
   cd Back-Office-Player
   python -m venv bopenv
   bopenv\Scripts\activate.bat
   pip install -r requirements.txt
   python app.py

Requires Python 3.10 or later.


First Launch
============

When BOP starts you will see the main window with:

* A **menu bar** (File, Edit, Playback, Settings, Help)
* An **Open audio file** button and file name label
* A **waveform display** (empty until a file is loaded)
* A **transport bar** (Play/Pause toggle, Stop) with a position slider
* **A/B loop controls** (Set A, Set B, Clear A/B, Loop A–B checkbox)
* A **tempo slider** and a **pitch slider**
* A **segment list** on the right
* A **practice session panel** at the bottom
* A **status bar** at the very bottom

The interface is also available in **French**: go to
**Settings → Language → Français**.


Opening an Audio File
=====================

* Click **Open audio file…** or press **Ctrl+O**.
* A file dialog opens. Select any supported audio file (MP3, WAV, FLAC, OGG,
  M4A, …).
* The waveform appears and the position slider becomes active.
* The application remembers the last folder you opened.

Recent files are listed under **File → Recent files** for quick access.


Transport Controls
==================

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Button
     - Shortcut
     - Action
   * - Play/Pause toggle
     - Ctrl+P
     - Start playback; or pause if already playing
   * - Stop
     - Ctrl+S
     - Stop playback and return to start of current loop (or file start)
   * - *(position slider)*
     - ← / →
     - Seek ±1 second; click anywhere on the slider to jump

The **status bar** confirms every action (e.g. "Playing test.mp3",
"Paused", "Stopped").


Volume
======

Use the **Volume** slider (below the transport bar) or press **Ctrl+Up** /
**Ctrl+Down** to adjust the output level (0–100 %).


A–B Loop
========

The A–B loop lets you repeat a precise section of the recording.

1. Start playback.
2. When the playhead reaches the desired start point, press **Set A**
   (Ctrl+Shift+A). The A marker appears on the waveform.
3. When the playhead reaches the desired end point, press **Set B**
   (Ctrl+Shift+B). The B marker appears.
4. Enable the **Loop A–B** checkbox (or press the shortcut) to activate
   looping. Playback will restart at A every time it reaches B.
5. Press **Clear A/B** to remove both markers.

You can also set A and B while stopped: the values are positions in
seconds (displayed in the status bar).


Named Segments
==============

You can save any A–B region as a **named segment** so you can return to it
later.

Saving a segment
-----------------

1. Set A and B.
2. Press **Save Segment** (Ctrl+Shift+S).
3. Enter a name in the dialog that appears and click **OK**.
4. The segment appears in the **Segment List** on the right.

Jumping to a segment
---------------------

* Double-click a segment in the list, or
* Select it and press **Enter** (or the **Jump** button).

The A and B markers jump to the segment boundaries and looping is enabled
automatically.

Deleting a segment
-------------------

* Select the segment and press **Delete** (or the **Delete** button in the
  list toolbar).
* Press **Ctrl+Z** to undo; **Ctrl+Y** to redo.

Moving a segment
-----------------

Use the **↑** and **↓** buttons in the segment list toolbar to change the
display order.

Filtering segments
-------------------

Use the **Category** drop-down above the segment list to show only segments
of a given category.

Exporting a segment
--------------------

Right-click a segment → **Export as WAV** or **Export as MP3** to save the
audio slice to a file.

.. note::

   MP3 export requires the ``lameenc`` library.  If it is not installed the
   option is greyed out.  Install it with ``pip install lameenc``.


Export / Import Configuration
==============================

You can save **all segments and settings** for a recording to a ``.bop``
file and share it with other users, or reload it later on a different
computer.

* **File → Export config…** (Ctrl+E): saves segments + playback settings.
* **File → Import config…** (Ctrl+I): loads a ``.bop`` file back. Existing
  segments are replaced after confirmation.


Tempo Control
=============

The **Tempo** slider (range: 50 %–200 %) changes the playback speed.

* 100 % = original speed
* 50 % = half speed (easier to follow difficult passages)
* 200 % = double speed

Use the **Up/Down arrow** keys on the focused slider to change the value in
5 % steps. The current value is shown next to the slider (e.g. "75%") and
announced to screen readers in real time.

The last used tempo is saved and restored the next time you open the same
recording.

Pitch-preserving tempo
-----------------------

Enable **Pitch-preserving** (checkbox next to the pitch slider) to change
the speed **without changing the pitch** (time-stretching). This is the most
natural-sounding mode for practice but uses more CPU.

When disabled (tape mode), slowing down also lowers the pitch — some students
prefer this for ear-training.


Pitch Control
=============

The **Pitch** slider shifts the pitch by ±12 semitones without changing the
playback speed. This is useful for transposing a recording to match your
instrument's tuning.

* 0 = no change
* +12 = one octave up
* −12 = one octave down

Semitone values are announced to the screen reader on every change.


Practice Session — Progressive Tempo
=====================================

The **Practice Session** panel (bottom of the window) automates the
common "start slow, get faster" practice routine.

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Description
   * - Loop count
     - Number of loops before stopping (0 = infinite)
   * - Loop delay (s)
     - Pause between loops in seconds
   * - Progressive tempo
     - Check to enable automatic tempo ramping
   * - Start tempo
     - Initial tempo as a fraction (e.g. 0.7 = 70 %)
   * - Step
     - Amount added to tempo after each loop (e.g. 0.05 = +5 %)
   * - Target tempo
     - Tempo at which the session stops (e.g. 1.0 = 100 %)

Starting a session
-------------------

1. Set the A–B loop and configure the panel.
2. Click **Start session** (or press the shortcut).
3. Press **Play** to begin. The tempo advances automatically after each loop.
4. When the target is reached (or the loop count is exhausted) the session
   stops and a summary is added to the Practice History.


Practice History
================

Every completed session is automatically recorded.

* Go to **Settings → Practice History…** (Ctrl+H) to open the history viewer.
* The table shows: date, audio file, duration, loops completed, average tempo.
* Click **Export CSV…** to save the full history as a spreadsheet.


Keyboard Shortcuts Reference
=============================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Shortcut
     - Action
   * - Ctrl+O
     - Open audio file
   * - Ctrl+P
     - Play / Pause toggle
   * - Ctrl+S
     - Stop
   * - Ctrl+Shift+A
     - Set loop point A
   * - Ctrl+Shift+B
     - Set loop point B
   * - Ctrl+Shift+S
     - Save current A–B region as a named segment
   * - Ctrl+E
     - Export practice config (.bop)
   * - Ctrl+I
     - Import practice config (.bop)
   * - Ctrl+H
     - Open practice history
   * - Ctrl+Z
     - Undo last segment operation
   * - Ctrl+Y
     - Redo
   * - Ctrl+Q
     - Quit
   * - ← / → (position slider)
     - Seek ±1 second
   * - ↑ / ↓ (tempo slider)
     - ±5 % tempo
   * - ↑ / ↓ (pitch slider)
     - ±1 semitone

All shortcuts can be customised via **Settings → Preferences → Shortcuts**.


Preferences
===========

Open **Settings → Preferences…** to change:

* **Shortcuts** — reassign any keyboard shortcut
* **Theme** — Default, Dark, or High Contrast
* **Language** — English or French
* **Accessibility**

  * *Position announce interval* — how often (in seconds) the current
    playback position is spoken by the screen reader (0 = off)

* **Audio** — future audio device selection


Accessibility Notes
===================

BOP is designed to be fully usable with a screen reader:

* All controls have accessible names and descriptions.
* Full keyboard navigation (Tab/Shift+Tab); transport controls come first
  in the tab order.
* The **position slider** is announced as ``mm:ss / mm:ss`` (current /
  total), not as a raw number.
* Tempo and pitch slider values are announced immediately after each change
  (assertive live region).
* The status bar announces every significant event.
* Tested with **NVDA** and **JAWS** on Windows 10/11.


Uninstalling
============

BOP does not write to the Windows registry. To remove it:

1. Delete the folder where you extracted ``BackOfficePlayer.exe``.
2. Optionally, delete the settings and history files stored in your user
   data directory (displayed under **Help → About…**):

   ``%LOCALAPPDATA%\BLIND SYSTEMS\Back-Office Player\``


Troubleshooting
===============

The application does not start
---------------------------------

* Make sure you extracted the full ZIP (not just the .exe).
* Try running from a terminal to see error output:

  .. code-block:: bat

     BackOfficePlayer.exe

* Antivirus software may quarantine the executable on first run. Add an
  exception for the BOP folder.

No sound
---------

* Check that your system sound is not muted.
* Try a different audio file.
* If using an external audio interface, BOP uses the Windows default output
  device. Set your interface as the default in Windows Sound Settings.

MP3 export button is greyed out
---------------------------------

The ``lameenc`` library is not bundled in the standalone executable. To
enable MP3 export when running from source::

   pip install lameenc

Slow tempo-change response
---------------------------

Enable **Pitch-preserving** mode only when you need it — it requires
real-time time-stretching which is CPU-intensive. In tape mode (unchecked),
tempo changes take effect instantly.


Support & Source Code
=====================

* GitHub: https://github.com/aminekhettat/Back-Office-Player
* Issues / feature requests: https://github.com/aminekhettat/Back-Office-Player/issues
* Author: Amine Khettat — amine.khettat@blindsystems.org


License
=======

Copyright © 2025–2026 BLIND SYSTEMS.
Distributed under the **Apache License 2.0**.
See the ``LICENSE`` file for the full text.
