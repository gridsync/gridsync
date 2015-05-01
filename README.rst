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


Installation
------------

Stable versions from PyPI:

``pip install gridsync``



TODO
----

* Logging
* Tor integration
* Client/server architecture
* Packaging
