========
Gridsync
========

Gridsync is a cross-platform, graphical user interface for `Tahoe-LAFS`_, the Least-Authority File Store. It is intended to simplify the configuration and management of locally-running Tahoe-LAFS gateways and to provide user-friendly mechanisms for backing up local files, synchronizing directories between devices, and sharing files and storage resources with other users across all major desktop platforms (GNU/Linux, Mac OS X, and Windows). More simply, Gridsync aims to duplicate most of the core functionality provided by other, proprietary "cloud" backup/synchronization services and utilities (such as Dropbox and BitTorrent Sync) but without demanding any sacrifice of the user's privacy or freedom -- and without requiring usage or knowledge of the command line.

.. _Tahoe-LAFS: https://tahoe-lafs.org

Why Gridsync?
-------------

Tahoe-LAFS already provides a number of desirable properties for file-storage: it is secure, decentralized, highly robust, free (as in both beer and speech), stable and mature, and written by a group of very talented developers. Unfortunately -- and despite all of its merits -- Tahoe-LAFS lacks where many of its competitors excel: its installatation requires heavy-usage of the command line, its configuration consists in hand-editing text files, and many of its fundamental concepts (e.g., "dircap", "servers-of-happiness") are opaque or otherwise demand additional reading of the project's extensive documentation. Accordingly, Tahoe-LAFS' userbase consists primarily in seasoned developers and system administrators; average users are naturally excluded from enjoying Tahoe-LAFS' aferomentioned advantages.

The Gridsync project intends to overcome some of Tahoe-LAFS' barriers-to-adoption by means of following features:

* A graphical user interface for managing all primary Tahoe-LAFS gateway functionality (e.g., starting, stopping, configuring nodes) -- the user will never have to edit a text file by hand.
* Native look and feel -- Gridsync uses the Qt application framework, emulating native widgets on all target platforms; the user can expect Gridsync to behave like any other desktop application.
* Local filesystem monitoring -- Gridsync watches for local changes to files and directories (via inotify/FSEvents/kqueue/ReadDirectoryChangesW) and can automate backup operations.
* Remote filesystem monitoring -- Gridsync periodically polls for changes in remote storage grids, providing basic synchronization functionality.
* Status indicators and desktop notifications -- the user will know, at a glance, when files are being uploaded or downloaded (via system tray icon animations) and will optionally receive notifications (via DBus on GNU/Linux, Growl/Nofication Center on OS X, etc.) when operations have completed.
* 'One-click' sharing -- similar to BitTorrent ``magnet:`` links, the IANA-friendly `Gridsync URI specification`_ allows users to easily join friends' storage grids or to synchronize remote Tahoe-LAFS directories with the local filesystem.
* OS/Desktop-level integration -- Gridsync will (optionally) run at startup, install URI-handlers, provide context menus for file-sharing in file managers, etc.

.. _Gridsync URI specification: https://github.com/gridsync/gridsync/blob/master/docs/uri_scheme.rst


Current (complete -- or nearly complete) features:
--------------------------------------------------

* Local filesystem monitoring (complete, all platforms).
* Locate and manage (create/start/stop) local Tahoe-LAFS nodes.
* Remote filesystem polling
* Bi-directional synchronization (some caveats, one race condition; more testing needed)
* System tray icon animations (complete, tested Linux, OS X)
* Unified JSON configuration format.
* Server/client architecture.
* Handle ``gridsync://`` links (partial)
* Desktop notifications (Linux only)


In development / TODO before first release (July 2015):
-------------------------------------------------------

* Finish URI-handler
* Finish Webkit wrapper
* More unit-tests / better test coverage, CI
* OS X, Windows desktop notifications
* Improve Tahoe configuration dialog, first-run wizard
* Better logging
* Better icons


Planned features (after first release):
---------------------------------------

* Packaging (PyPI, Debian, RPM, ebuild, pyinstaller)
* i18n/L10n
* File manager/context menu integration
* Tor/I2P integration
* NAT traversal (via UPnP?)


Current dependences
-------------------

* `Tahoe-LAFS`_
* `Qt4`_
* `PyQt4`_
* `qt4reactor`_
* `watchdog`_

.. _Qt4: http://download.qt.io/archive/qt/4.8/4.8.6/
.. _PyQT4: http://www.riverbankcomputing.com/software/pyqt/download
.. _qt4reactor: https://github.com/ghtdak/qtreactor
.. _watchdog: https://pypi.python.org/pypi/watchdog


LICENSE
-------

Gridsync will be released as Free Software under the GPL license.

