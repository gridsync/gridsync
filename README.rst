========
Gridsync
========

  **WARNING**: *At present, Gridsync is in the very early stages of development and planning and, like many other Free and Open Source projects, is severely lacking development resources; so long as this notice remains, all code should be considered broken, incomplete, bug-ridden, or in an extreme alpha state and should not be relied upon by anyone.* **Do not use this software for anything important!**

Gridsync is a cross-platform, graphical user interface for `Tahoe-LAFS`_, the Least Authority File Store. It is intended to simplify the configuration and management of locally-running Tahoe-LAFS gateways and to provide user-friendly mechanisms for seemlessly backing up local files, synchronizing directories between devices, and sharing files and storage resources with other users across all major desktop platforms (GNU/Linux, Mac OS X, and Windows). More simply, Gridsync aims to duplicate most of the core functionality provided by other, proprietary "cloud" backup/synchronization services and utilities (such as Dropbox and BitTorrent Sync) but without demanding any sacrifice of the user's privacy or freedom -- and without requiring usage or knowledge of the command line. Accordingly, Gridsync is developed under the principle that secure file storage and backups should be freely available to everyone, without exception, without added barriers, and regardless of one's operating system choice.

.. _Tahoe-LAFS: https://tahoe-lafs.org


Why Gridsync?
-------------

Tahoe-LAFS already provides a number of desirable properties for file-storage: it is secure, decentralized, highly robust, free (as in both beer and speech), stable and mature, and written by a group of very talented developers. Unfortunately -- and despite all of its technical merits -- Tahoe-LAFS lacks where many of its competitors excel: its installatation requires heavy-usage of the command line, its configuration consists in hand-editing text files, and many of its fundamental concepts (e.g., "dircap", "servers-of-happiness") are opaque or otherwise demand additional reading of the project's extensive documentation. Accordingly, Tahoe-LAFS' userbase consists primarily in seasoned developers and system administrators; "average" users are naturally excluded from enjoying Tahoe-LAFS' aforementioned advantages.

The Gridsync project intends to overcome some of Tahoe-LAFS' barriers-to-adoption by means of following features:

* A graphical user interface for managing all primary Tahoe-LAFS gateway functionality (e.g., starting, stopping, configuring nodes) -- the user will never have to edit a text file by hand.
* Native look and feel -- Gridsync uses the Qt application framework, emulating native widgets on all target platforms; the user can expect Gridsync to behave like any other desktop application.
* Local filesystem monitoring -- Gridsync watches for local changes to files and directories (via inotify/FSEvents/kqueue/ReadDirectoryChangesW) and can automate backup operations[*]_.
* Remote filesystem monitoring -- Gridsync periodically polls for changes in remote storage grids, providing basic synchronization functionality.
* Status indicators and desktop notifications -- the user will know, at a glance, when files are being uploaded or downloaded (via system tray icon animations) and will optionally receive notifications (via DBus on GNU/Linux, Notification Center on OS X, etc.) when operations have completed.
* 'One-click' sharing -- similar to BitTorrent ``magnet:`` links, the IANA-friendly `Gridsync URI specification`_ allows users to easily join friends' storage grids or to synchronize remote Tahoe-LAFS directories with the local filesystem.
* OS/Desktop-level integration -- Gridsync will (optionally) run at startup, install URI-handlers, provide context menus for file-sharing in file managers, etc.

.. _Gridsync URI specification: https://github.com/gridsync/gridsync/blob/master/docs/uri_scheme.rst

.. [*] It is worth mentioning that `Least Authority`_ has recently received OTF funding to develop Magic Folders, "a 'Dropbox-esque', friendly file-syncing utility," for Tahoe-LAFS. According to their own stated `objectives`_, however, Magic Folders will only target Linux and Windows (omitting, at least implicitly, Mac OS X and other BSD-based operating systems). It is also presently unknown whether the completed implementation of Magic Folders will include a desktop-oriented interface. As a result, the goals of the Gridsync project are likely to remain relevant and useful beyond the completion of Magic Folders' stated objectives.

.. _Least Authority: https://leastauthority.com/
.. _objectives: https://github.com/LeastAuthority/Open-Technology-Fund-Magic-Folders-Project/blob/master/objectives.rst

Brief UX sketch/outline
-----------------------

* User installs the application via a platform-specific installer (.dmg on OS X, etc.)
* User runs the application using their platform-specific method (double clicking on an application icon from a menu, dock, etc.)
* If the application has never been run before, an initial 'first run' welcome dialog is shown, briefly explaining and pointing out that the application is running in the system tray and can be accessed at any time. During this time, a background process scans for any already-installed/configured Tahoe-LAFS nodes (e.g., by looking for ~/.tahoe on Linux/OS X) and reads its aliases file to learn the user's dircaps
* If an already-configured Tahoe-LAFS node was found, the next screen prompts the user to pair its already-known Tahoe-LAFS dircaps with local directories using the platform-specific directory-selection dialog (provided by Qt)
* If no already-configured Tahoe-LAFS nodes were found, the next screen prompts the user to enter the appropriate settings required to get a gateway up and running (specificaly, by entering the appropriate values for the introducer fURL and specifying the desired redundancy levels). Alternatively, the user may paste in a ``gridsync://`` URI link (which already contains all of this information).
* After one or more Tahoe-LAFS gateways are configured, Gridsync stores a) all known Tahoe-LAFS gateway settings and b) all local-to-remote pairings in a JSON formatted configuration file and lauches each gateway in the background.
* After all gateway processes have successfully started, Gridsync performs its initial sync, scanning the metadata (file sizes, modification times) of local directories and comparing it against the latest snapshot stored in the associated grid for each local-to-remote pairing. During this time, the icon in the system tray spins clockwise.
* After the differences between the local and remote state are known, Gridsync downloads any new files from the latest known snapshot and uploads any local files not present in the grid. Any conflicts are tagged with ``.(conflicted copy %Y-%m-%d %H-%M-%S)`` and made known to the user via a platform-specific notification (Notification Center on OS X, DBus/libnotify on Linux)
* After the initial synchonization has completed, the main Gridsync background process sets up local filesystem watchers (via inotify/FSEvents/kqueue/ReadDirectoryChangesW using the python-watchdog library) to monitor for local filesystem changes and spawns polling timers to periodically check for new snapshots in the associated grids/dircaps.
* Whenever a local or remote change is detected, the synchonization process is re-run, however, these subsequent sync calls a) are faster than the initial (since the initial metadata crawl no longer needs to be performed) and b) provide platform-specific notifacions to the user (briefly indicating which files/directories have been synchronized).
* So long as the main Gridsync process continues to run, any ``gridsync://`` links passed to the program (e.g., by clicking the link in a browser or email) will present a dialog to the user prompting them to select local directory to which the remote content (specified in the link) should be synchronized. This makes it easy for friends of new users to share access to storage grids or stored files/directories without demanding that the new user configure a Tahoe-LAFS gateway manually.


Current (complete -- or nearly complete) features:
--------------------------------------------------

* Locate and manage (create/start/stop) local Tahoe-LAFS nodes.
* Local filesystem monitoring (complete, all platforms).
* Remote filesystem polling
* Bi-directional synchronization (some caveats, one race condition; more testing needed)
* System tray icon animations (complete, tested Linux, OS X)
* Unified JSON configuration format.
* Server/client architecture.
* Desktop notifications (Linux, OS X)
* Native installation for OS X (.dmg/.app)


In development / TODO / coming soon:
------------------------------------

* Finalize GUI design
* Connect dialogs/menus to server processes
* Finalize/implement ``gridsync://`` URI-handler,
* Finalize/implement 'one-click' sharing UX
* Unit/integration/system/user tests
* Tor integration
* Upload to PyPI


Planned features / coming later:
--------------------------------

* Windows packaging
* Linux distribution packaging (Debian, RPM, Arch PKGBUILD, Gentoo ebuilds, etc.)
* i18n/L10n
* File manager/context menu integration
* I2P integration
* NAT traversal (via UPnP?)
* Mobile/Android client


Installation:
-------------

Linux (Debian-based systems):

1. ``apt-get install tahoe-lafs python-qt4 python-pip``
2. ``pip install git+https://github.com/gridsync/gridsync.git``

Mac OS X [*]_ :

1. `Manually install Tahoe-LAFS`_ (*or* download/run the pre-built installer available `here`_)
2. Download `Gridsync (dmg)`_ and drag the contained Gridsync.app into your Applications folder (or anywhere)

Windows [*]_ :

(Coming soon)

.. _Manually install Tahoe-LAFS: https://tahoe-lafs.org/trac/tahoe-lafs/browser/trunk/docs/quickstart.rst
.. _here: https://github.com/gridsync/gridsync/releases/download/v0.0.1/tahoe-lafs-1.10.1.post3-osx.pkg
.. _Gridsync: https://github.com/gridsync/gridsync/releases/download/v0.0.1/Gridsync-PROTOTYPE-ALPHA.dmg

.. [*] In future OS X/Windows releases, Tahoe-LAFS will (hopefully) be bundled with Gridsync in a single, unified installer.


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

Contributions of any sort (e.g., suggestions, criticisms, bug reports, pull requests) are more than welcome! Any persons interested in aiding the development of Gridsync are encouraged to do so by opening a `GitHub Issue_` or by contacting its primary developer: `chris@gridsync.io`_

.. _GitHub Issue: https://github.com/crwood/gridsync/issues
.. _chris@gridsync.io: mailto:chris@gridsync.io

License:
--------

Gridsync is released as Free Software under the GPL license.

