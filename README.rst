========
Gridsync
========

Gridsync is a cross-platform desktop client for `Tahoe-LAFS`_, the Least-Authority File Store. It is intended to simplify the management and configuration of locally-running Tahoe-LAFS nodes and to provide user-friendly mechanisms for automating backup tasks and sharing stored files.

.. _Tahoe-LAFS: https://tahoe-lafs.org

Current features
----------------

* Manage and configure multiple local Tahoe-LAFS nodes
* Monitor local filesystem changes and perform automatic backups
* Bi-directional synchronization between local directories and remote Tahoe-LAFS storage grids


Planned features
----------------

* One click sharing of storage resources via "gridsync://" URI scheme
* Full Tor integration, for anonymous sharing of files and storage resources
* Grid-discovery
* i18n/L10n

Installation
------------

1. Install `Tahoe-LAFS`_
2. Install `Qt4`_
3. Install `PyQt4`_
4. Install pip
5. ``pip install gridsync``

.. _Qt4: http://download.qt.io/archive/qt/4.8/4.8.6/
.. _PyQT4: http://www.riverbankcomputing.com/software/pyqt/download

(If installing Tahoe-LAFS from pip on GNU/Linux, ``apt-get install python-dev build-essential libffi-dev libssl-dev``)


TODO
----


* Logging
* Better icons
* Packaging
* Tor integration


FAQ
---

* Q: Why the name "Gridsync," why not "Tahoe-LAFS desktop client," "Tahoe-LAFS-Sync," etc.?
  * A: The name "Tahoe-LAFS" is bad for the purposes of mass-adoption; even with its abreviation expanded, it does little to convey its usage or purpose to the average end-user (and the average end-user *thinks* in terms of usage patterns and end purposes). At least "Gridsync" tacitly conveys the most typical use-case for Tahoe-LAFS, i.e., the transfer of files to and from a storage grid.

* Q: What about Tahoe-LAFS's file-sharing capabilities, or its security properties?
  * A: File-sharing is a secondary property by necessity: users can synchronize files without sharing them but they can't share without synchronizing. Regarding security, it's high time that private file storage and transfer became the norm, not the exception; privacy tools fail to become adopted because they're not friendly enough or marketed towards a diverse userbase, not because their security properties aren't attractive.




