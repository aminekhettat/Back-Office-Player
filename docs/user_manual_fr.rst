.. _user_manual_fr:

==========================================================
Back-Office Player — Manuel d'utilisation (Français)
==========================================================

| **Version :** 2.0.0
| **Date :** 19 avril 2026
| **Auteur :** Amine Khettat — BLIND SYSTEMS
| **Contact :** amine.khettat@blindsystems.org
| **Licence :** Apache-2.0

.. contents:: Table des matières
   :depth: 3
   :local:


Introduction
============

**Back-Office Player (BOP)** est un outil musical gratuit et accessible,
conçu pour les élèves musiciens. Il vous permet d'ouvrir un enregistrement
audio (MP3, WAV, FLAC, …), de marquer des passages à travailler, de les
répéter en boucle à vitesse réduite, puis d'augmenter progressivement le
tempo — sans souris, grâce à la navigation clavier complète et à la
compatibilité avec les lecteurs d'écran.

BOP a été développé par `BLIND SYSTEMS <https://www.blindsystems.org>`_ pour
les élèves de l'association
`Culture Musique / Saba Music <https://www.sabamusic.fr>`_.


Configuration requise
=====================

* **Système d'exploitation :** Windows 10 ou Windows 11 (64 bits)
* **Connexion Internet :** uniquement pour la vérification des mises à jour
  (désactivable dans les Préférences)
* Aucune installation de Python requise — l'exécutable ``BackOfficePlayer.exe``
  contient tout le nécessaire


Installation
============

Exécutable autonome (recommandé)
----------------------------------

1. Téléchargez ``BackOfficePlayer-2.0.0-win64.zip`` depuis la
   `page des releases GitHub <https://github.com/aminekhettat/Back-Office-Player/releases>`_.
2. Extrayez le ZIP où vous le souhaitez (par exemple ``C:\Programmes\BOP\``).
3. Double-cliquez sur ``BackOfficePlayer.exe`` pour lancer l'application.
4. Windows SmartScreen peut afficher un avertissement lors du premier lancement.
   Cliquez sur **Informations complémentaires → Exécuter quand même**.

Aucune installation, aucune entrée dans le registre, aucun droit
administrateur requis.


Exécution depuis les sources
-----------------------------

.. code-block:: bash

   git clone https://github.com/aminekhettat/Back-Office-Player.git
   cd Back-Office-Player
   python -m venv bopenv
   bopenv\Scripts\activate.bat
   pip install -r requirements.txt
   python app.py

Requiert Python 3.10 ou supérieur.


Premier démarrage
=================

À l'ouverture de BOP, vous verrez la fenêtre principale avec :

* Une **barre de menus** (Fichier, Édition, Lecture, Paramètres, Aide)
* Un bouton **Ouvrir un fichier audio** et un label de nom de fichier
* Un **affichage de forme d'onde** (vide jusqu'au chargement d'un fichier)
* Une **barre de transport** (bascule Lecture/Pause, Arrêt) avec un curseur
  de position
* Les **contrôles de boucle A/B** (Fixer A, Fixer B, Effacer A/B, case Boucle A–B)
* Un **curseur de tempo** et un **curseur de hauteur**
* Une **liste de segments** à droite
* Un **panneau de session de travail** en bas
* Une **barre d'état** tout en bas

L'interface est disponible en anglais : allez dans
**Paramètres → Langue → English**.


Ouvrir un fichier audio
========================

* Cliquez sur **Ouvrir un fichier audio…** ou appuyez sur **Ctrl+O**.
* Une boîte de dialogue s'ouvre. Sélectionnez n'importe quel fichier audio
  compatible (MP3, WAV, FLAC, OGG, M4A, …).
* La forme d'onde s'affiche et le curseur de position devient actif.
* L'application mémorise le dernier dossier utilisé.

Les fichiers récents sont accessibles via **Fichier → Fichiers récents**.


Commandes de transport
======================

.. list-table::
   :header-rows: 1
   :widths: 35 20 45

   * - Bouton
     - Raccourci
     - Action
   * - Bascule Lecture/Pause
     - Ctrl+P
     - Lance la lecture ; met en pause si déjà en cours
   * - Arrêt
     - Ctrl+S
     - Arrête la lecture et revient au début de la boucle (ou du fichier)
   * - *(curseur de position)*
     - ← / →
     - Avance/recule de ±1 seconde ; cliquez pour sauter à un point précis

La **barre d'état** confirme chaque action (ex. : « Lecture de test.mp3 »,
« En pause », « Arrêté »).


Volume
======

Utilisez le curseur **Volume** (sous la barre de transport) ou appuyez sur
**Ctrl+Haut** / **Ctrl+Bas** pour régler le niveau de sortie (0–100 %).


Boucle A–B
==========

La boucle A–B permet de répéter précisément une section de l'enregistrement.

1. Lancez la lecture.
2. Quand le curseur de lecture atteint le début souhaité, appuyez sur
   **Fixer A** (Ctrl+Shift+A). Le marqueur A apparaît sur la forme d'onde.
3. Quand le curseur atteint la fin souhaitée, appuyez sur **Fixer B**
   (Ctrl+Shift+B). Le marqueur B apparaît.
4. Cochez **Boucle A–B** pour activer le bouclage. La lecture repart depuis A
   chaque fois qu'elle atteint B.
5. Appuyez sur **Effacer A/B** pour supprimer les deux marqueurs.

Vous pouvez aussi fixer A et B pendant la pause ; les valeurs sont des
positions en secondes (affichées dans la barre d'état).


Segments nommés
===============

Vous pouvez enregistrer n'importe quelle région A–B comme **segment nommé**
pour y revenir facilement.

Enregistrer un segment
-----------------------

1. Fixez A et B.
2. Appuyez sur **Sauvegarder le segment** (Ctrl+Shift+S).
3. Entrez un nom dans la boîte de dialogue et cliquez sur **OK**.
4. Le segment apparaît dans la **Liste des segments** à droite.

Sauter vers un segment
-----------------------

* Double-cliquez sur le segment dans la liste, ou
* Sélectionnez-le et appuyez sur **Entrée** (ou le bouton **Sauter**).

Les marqueurs A et B se positionnent automatiquement sur les bornes du
segment et la boucle est activée.

Supprimer un segment
---------------------

* Sélectionnez le segment et appuyez sur **Suppr** (ou le bouton **Supprimer**
  dans la barre d'outils).
* Appuyez sur **Ctrl+Z** pour annuler ; **Ctrl+Y** pour rétablir.

Déplacer un segment
--------------------

Utilisez les boutons **↑** et **↓** de la barre d'outils pour modifier
l'ordre d'affichage.

Filtrer les segments
---------------------

Utilisez la liste déroulante **Catégorie** au-dessus de la liste des segments
pour n'afficher qu'une catégorie donnée.

Exporter un segment
--------------------

Clic droit sur un segment → **Exporter en WAV** ou **Exporter en MP3** pour
sauvegarder la portion audio dans un fichier.

.. note::

   L'export MP3 nécessite la bibliothèque ``lameenc``.
   Si elle n'est pas installée, l'option est grisée.
   Pour l'activer : ``pip install lameenc``.


Exporter / importer une configuration
======================================

Vous pouvez sauvegarder **tous les segments et paramètres** d'un
enregistrement dans un fichier ``.bop`` et le partager ou le recharger
ultérieurement.

* **Fichier → Exporter la config…** (Ctrl+E) : enregistre segments +
  paramètres de lecture.
* **Fichier → Importer la config…** (Ctrl+I) : charge un fichier ``.bop``.
  Les segments existants sont remplacés après confirmation.


Contrôle du tempo
=================

Le curseur **Tempo** (plage : 50 %–200 %) modifie la vitesse de lecture.

* 100 % = vitesse originale
* 50 % = demi-vitesse (idéal pour les passages difficiles)
* 200 % = double vitesse

Utilisez les flèches **Haut/Bas** sur le curseur actif pour changer la
valeur par pas de 5 %. La valeur courante est affichée à côté du curseur
(ex. : « 75 % ») et annoncée en temps réel aux lecteurs d'écran.

Le dernier tempo utilisé est sauvegardé et restauré à la prochaine ouverture
du même enregistrement.

Tempo avec préservation de la hauteur
--------------------------------------

Activez **Préservation de la hauteur** (case à cocher à côté du curseur de
hauteur) pour modifier la vitesse **sans changer la hauteur** (time-stretching).
C'est le mode le plus naturel pour travailler, mais il utilise davantage de
ressources processeur.

En mode désactivé (mode « bande »), ralentir l'enregistrement abaisse aussi
la hauteur — certains élèves préfèrent ce comportement pour l'éducation de
l'oreille.


Contrôle de la hauteur
=======================

Le curseur **Hauteur** décale la tonalité de ±12 demi-tons sans modifier la
vitesse de lecture. Pratique pour transposer un enregistrement afin de
l'accorder à votre instrument.

* 0 = aucun changement
* +12 = une octave plus haut
* −12 = une octave plus bas

Les valeurs en demi-tons sont annoncées au lecteur d'écran à chaque
modification.


Session de travail — Tempo progressif
=======================================

Le panneau **Session de travail** (bas de la fenêtre) automatise la méthode
classique « commencer lent, accélérer progressivement ».

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Paramètre
     - Description
   * - Nombre de boucles
     - Nombre de répétitions avant arrêt (0 = infini)
   * - Délai entre boucles (s)
     - Pause en secondes entre deux boucles
   * - Tempo progressif
     - Cochez pour activer l'augmentation automatique du tempo
   * - Tempo de départ
     - Tempo initial (ex. : 0,7 = 70 %)
   * - Incrément
     - Quantité ajoutée au tempo après chaque boucle (ex. : 0,05 = +5 %)
   * - Tempo cible
     - Tempo auquel la session s'arrête (ex. : 1,0 = 100 %)

Démarrer une session
---------------------

1. Fixez la boucle A–B et configurez le panneau.
2. Cliquez sur **Démarrer la session** (ou utilisez le raccourci).
3. Appuyez sur **Lecture**. Le tempo avance automatiquement après chaque
   boucle.
4. Quand le tempo cible est atteint (ou le nombre de boucles épuisé), la
   session s'arrête et un résumé est ajouté à l'Historique de travail.


Historique de travail
=====================

Chaque session terminée est enregistrée automatiquement.

* Allez dans **Paramètres → Historique de travail…** (Ctrl+H) pour ouvrir
  le visualisateur d'historique.
* Le tableau affiche : date, fichier audio, durée, boucles effectuées, tempo
  moyen.
* Cliquez sur **Exporter CSV…** pour sauvegarder l'historique complet sous
  forme de tableau.


Récapitulatif des raccourcis clavier
=====================================

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Raccourci
     - Action
   * - Ctrl+O
     - Ouvrir un fichier audio
   * - Ctrl+P
     - Bascule Lecture / Pause
   * - Ctrl+S
     - Arrêt
   * - Ctrl+Shift+A
     - Fixer le point de boucle A
   * - Ctrl+Shift+B
     - Fixer le point de boucle B
   * - Ctrl+Shift+S
     - Sauvegarder la région A–B en tant que segment nommé
   * - Ctrl+E
     - Exporter la config de travail (.bop)
   * - Ctrl+I
     - Importer une config de travail (.bop)
   * - Ctrl+H
     - Ouvrir l'historique de travail
   * - Ctrl+Z
     - Annuler la dernière opération sur les segments
   * - Ctrl+Y
     - Rétablir
   * - Ctrl+Q
     - Quitter
   * - ← / → (curseur de position)
     - Avancer / reculer de ±1 seconde
   * - ↑ / ↓ (curseur de tempo)
     - ±5 % de tempo
   * - ↑ / ↓ (curseur de hauteur)
     - ±1 demi-ton

Tous les raccourcis peuvent être personnalisés via
**Paramètres → Préférences → Raccourcis**.


Préférences
===========

Ouvrez **Paramètres → Préférences…** pour modifier :

* **Raccourcis** — réassignez n'importe quel raccourci clavier
* **Thème** — Par défaut, Sombre, ou Contraste élevé
* **Langue** — Français ou English
* **Accessibilité**

  * *Intervalle d'annonce de position* — fréquence (en secondes) à laquelle
    la position de lecture courante est annoncée par le lecteur d'écran
    (0 = désactivé)

* **Audio** — sélection du périphérique audio (à venir)


Notes d'accessibilité
=====================

BOP est conçu pour être entièrement utilisable avec un lecteur d'écran :

* Tous les contrôles ont un nom et une description accessibles.
* Navigation clavier complète (Tab/Shift+Tab) ; les contrôles de transport
  sont en premier dans l'ordre de tabulation.
* Le **curseur de position** est annoncé comme ``mm:ss / mm:ss`` (position
  courante / durée totale), et non comme un nombre brut.
* Les valeurs des curseurs de tempo et de hauteur sont annoncées immédiatement
  après chaque modification (région active assertive).
* La barre d'état annonce chaque événement important.
* Testé avec **NVDA** et **JAWS** sous Windows 10/11.


Désinstallation
===============

BOP n'écrit rien dans le registre Windows. Pour le supprimer :

1. Supprimez le dossier dans lequel vous avez extrait ``BackOfficePlayer.exe``.
2. Supprimez éventuellement les fichiers de paramètres et d'historique
   stockés dans votre dossier de données utilisateur (affiché dans
   **Aide → À propos…**) :

   ``%LOCALAPPDATA%\BLIND SYSTEMS\Back-Office Player\``


Résolution des problèmes
=========================

L'application ne démarre pas
------------------------------

* Assurez-vous d'avoir extrait l'intégralité du ZIP (pas uniquement le .exe).
* Essayez de lancer depuis un terminal pour voir les messages d'erreur :

  .. code-block:: bat

     BackOfficePlayer.exe

* Un antivirus peut mettre le fichier en quarantaine au premier lancement.
  Ajoutez une exception pour le dossier BOP.

Pas de son
-----------

* Vérifiez que le son système n'est pas coupé.
* Essayez un autre fichier audio.
* Si vous utilisez une interface audio externe, BOP utilise le périphérique
  de sortie par défaut de Windows. Définissez votre interface comme
  périphérique par défaut dans les Paramètres audio Windows.

Le bouton d'export MP3 est grisé
----------------------------------

La bibliothèque ``lameenc`` n'est pas incluse dans l'exécutable autonome.
Pour activer l'export MP3 en exécution depuis les sources ::

   pip install lameenc

Réponse lente au changement de tempo
--------------------------------------

N'activez le mode **Préservation de la hauteur** que lorsque vous en avez
besoin — il requiert un time-stretching en temps réel, intensif en CPU. En
mode bande (désactivé), les changements de tempo sont instantanés.


Support et code source
=======================

* GitHub : https://github.com/aminekhettat/Back-Office-Player
* Signaler un problème / demander une fonctionnalité :
  https://github.com/aminekhettat/Back-Office-Player/issues
* Auteur : Amine Khettat — amine.khettat@blindsystems.org


Licence
=======

Copyright © 2025–2026 BLIND SYSTEMS.
Distribué sous la **licence Apache 2.0**.
Consultez le fichier ``LICENSE`` pour le texte complet.
