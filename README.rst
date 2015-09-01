========
Gridsync
========

  **WARNING**: *At present, Gridsync is in the very early stages of development and planning and, like many other Free and Open Source projects, is severely lacking development resources; so long as this notice remains, all code should be considered broken, incomplete, bug-ridden, or in an extreme alpha state and should not be relied upon seriously by anyone.* **Do not use this software for anything important!**

Gridsync is an experimental cross-platform, graphical user interface for `Tahoe-LAFS`_, the Least Authority File Store. It is intended to simplify the configuration and management of locally-running Tahoe-LAFS gateways and to provide user-friendly mechanisms for seemlessly backing up local files, synchronizing directories between devices, and sharing files and storage resources with other users across all major desktop platforms (GNU/Linux, Mac OS X, and Windows). More simply, Gridsync aims to duplicate most of the core functionality provided by other, proprietary "cloud" backup/synchronization services and utilities (such as Dropbox and BitTorrent Sync) but without demanding any sacrifice of the user's privacy or freedom -- and without requiring usage or knowledge of the command line. Accordingly, Gridsync is developed under the principle that secure file storage and backups should be freely available to everyone, without exception, without added barriers, and regardless of one's operating system choice.

.. _Tahoe-LAFS: https://tahoe-lafs.org


Why Gridsync?
-------------

Tahoe-LAFS already provides a number of desirable properties for file-storage: it is secure, decentralized, highly robust, free (as in both beer and speech), stable and mature, and written by a group of very talented developers. Unfortunately -- and despite all of its technical merits -- Tahoe-LAFS lacks where many of its competitors excel: its installatation requires heavy-usage of the command line, its configuration consists in hand-editing text files, and many of its fundamental concepts (e.g., "dircap", "servers-of-happiness") are opaque or otherwise demand additional reading of the project's extensive documentation. Accordingly, Tahoe-LAFS' userbase consists primarily in seasoned developers and system administrators; "average" users are naturally excluded from enjoying Tahoe-LAFS' aforementioned advantages.

The Gridsync project intends to overcome some of Tahoe-LAFS' barriers-to-adoption by means of following features:

* A graphical user interface for managing all primary Tahoe-LAFS gateway functionality (e.g., starting, stopping, configuring nodes) -- the user will never have to edit a text file by hand.
* Native look and feel -- Gridsync uses the Qt application framework, emulating native widgets on all target platforms; the user can expect Gridsync to behave like any other desktop application.
* Local filesystem monitoring -- Gridsync watches for local changes to files and directories (via inotify/FSEvents/kqueue/ReadDirectoryChangesW) and can automate backup operations [*]_ .
* Remote filesystem monitoring -- Gridsync periodically polls for changes in remote storage grids, providing basic synchronization functionality.
* Status indicators and desktop notifications -- the user will know, at a glance, when files are being uploaded or downloaded (via system tray icon animations) and will optionally receive notifications (via DBus on GNU/Linux, Notification Center on OS X, etc.) when operations have completed.
* 'One-click' sharing -- similar to BitTorrent ``magnet:`` links, the IANA-friendly `Gridsync URI specification`_ allows users to easily join others' storage grids or to synchronize remote Tahoe-LAFS directories with the local filesystem.
* OS/Desktop-level integration -- Gridsync will (optionally) run at startup, install OS-level URI-handlers, provide context menus for sharing files directly in popular desktop file managers, etc.

.. _Gridsync URI specification: https://github.com/gridsync/gridsync/blob/master/docs/uri_scheme.rst

.. [*] It is worth mentioning that `Least Authority`_ has recently received OTF funding to develop Magic Folders, "a 'Dropbox-esque', friendly file-syncing utility," for Tahoe-LAFS. According to their own stated `objectives`_, however, Magic Folders will only target Linux and Windows (omitting, at least implicitly, Mac OS X and other BSD-based operating systems). It is also presently unknown whether the completed implementation of Magic Folders will include a desktop-oriented interface. As a result, the goals of the Gridsync project are likely to remain relevant and useful beyond the completion of Magic Folders' stated objectives.

.. _Least Authority: https://leastauthority.com/
.. _objectives: https://github.com/LeastAuthority/Open-Technology-Fund-Magic-Folders-Project/blob/master/objectives.rst


Screenshots
-----------

Gridsync uses Qt to emulate native widgets across all three major desktop platforms:

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/tutorial.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/osx-prefs.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/preferences-dialog.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/81e91c93ae1b9418f147d6eea043948ac449dab5/images/screenshots/new-sync-folder.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/sync-complete.png


Current (complete -- or nearly complete) features:
--------------------------------------------------

* Native (.dmg/.app) installation for OS X
* User-friendly initial setup tutorial
* Background daemon to manage (create/start/stop) multiple local Tahoe-LAFS nodes.
* Local filesystem monitoring (complete, all platforms).
* Remote filesystem polling.
* Bi-directional synchronization (partial/broken; see below).
* System tray icon animations.
* Desktop notifications (GNU/Linux, OS X)
* Simple unified YAML configuration format.


In development / TODO / coming soon:
------------------------------------

* Generate Preferences dialog from settings and connect signals/slots
* Complete Tor integration
* Finalize/implement ``gridsync://`` URI-handler and 'one-click' sharing UX/UI
* Finalizy/implement "rollback" UI (a-la OS X "Time Machine" for reverting to previous backups/snapshots)
* Unit/integration/system/user tests
* Improved sync algorithm
* Windows packaging
* Upload to PyPI


Planned features / coming later:
--------------------------------

* GNU/Linux distribution packaging (Debian, RPM, Arch PKGBUILD, Gentoo ebuilds, etc.)
* i18n/L10n
* File manager/context menu integration for Finder (OS X), Explorer (Windows), Nautilus, Konqueror, Thunar, etc. (GNU/Linux)
* Visual/animated 'map' of shares distribution (think: a graphical version of https://bigasterisk.com/tahoe-playground/)
* I2P integration
* NAT traversal (via UPnP?)
* Mobile/Android client


Known issues / caveats:
-----------------------

* The watcher/syncing code is very hackish and is currently broken in several ways (file-deletion isn't yet handled, there are numerous race conditions, the threading model needs to be overhauled/replaced, etc.); don't expect bi-directional sync to work well yet (this code may even go away entirely, being superseded by Tahoe-LAFS' upcoming "Magic Folders").
* Dircaps/filecaps presently leak to $config_dir/gridsync.log, $config_dir/gridsync.yml, and the process list. These will be fixed soon.
* The OS X .dmg/.app bundle is quite large (~90 megs) as it includes its own python interpreter, parts of the Qt library, and a full Tahoe-LAFS install (along with all of its dependencies, tests, etc.). This should be trimmed down significantly in the future.
* The Preferences dialog is currently a placeholder form prototyped in QtDesigner and generated by pyuic4. Its buttons do not (yet) do anything. This will be fixed soon (along with the missing "Add new storage grid" interface).
* Desktop notifications are currently spammy and trigger on every sync. This too will be fixed: notifications will only trigger for rare-events (receiving a new file from a friend, restoring from a previous snapshot, etc.) and will be more informative generally (specifying the name of the file(s) received, etc.)
* Nothing has been tried/tested on Windows yet.


Installation:
-------------

Linux (Debian-based systems):

1. ``apt-get install tahoe-lafs python-qt4 python-pip``
2. ``pip install git+https://github.com/gridsync/gridsync.git``

Mac OS X [*]_ :

1. Download `Gridsync.dmg`_ and drag the contained Gridsync.app into your Applications folder.

Windows:

(Coming soon)

.. _Gridsync.dmg: https://github.com/gridsync/gridsync/releases/download/0.0.1-ALPHA1/Gridsync-0.0.1-ALPHA1.dmg

.. [*] Mac OS X users may have to explicitly allow third-party apps in order to use Gridsync ("System Preferences" -> "Security & Privacy" -> "General" -> "Allow apps downloaded from:" -> "Anywhere").


Running:
--------

Linux:

* From the command-line: ``gridsync`` (or ``gridsync --help`` for available options)

Mac OS X:

* Double click the previously-installed Gridsync.app

Windows:

(Coming soon...)


Contributing:
-------------

Contributions of any sort (e.g., suggestions, criticisms, bug reports, pull requests) are more than welcome. Any persons interested in aiding the development of Gridsync are encouraged to do so by opening a `GitHub Issue`_ or by contacting its primary developer: `chris@gridsync.io`_

.. _GitHub Issue: https://github.com/crwood/gridsync/issues
.. _chris@gridsync.io: mailto:chris@gridsync.io

License:
--------

Gridsync is released as Free Software under the GPL license.

----

.. image:: 
:target: https://travis-ci.org/gridsync/gridsync

.. image:: 
:target: https://coveralls.io/github/gridsync/gridsync?branch=master

