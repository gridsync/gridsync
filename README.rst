========
Gridsync
========

.. image:: https://api.travis-ci.org/gridsync/gridsync.svg?branch=master
    :target: https://travis-ci.org/gridsync/gridsync
.. image:: https://ci.appveyor.com/api/projects/status/li99vnfax895i8oy/branch/master?svg=true
    :target: https://ci.appveyor.com/project/crwood/gridsync
.. image:: https://buildbot.gridsync.io/png?builder=linux
    :target: https://buildbot.gridsync.io/builders/linux
.. image:: https://buildbot.gridsync.io/png?builder=mac
    :target: https://buildbot.gridsync.io/builders/mac
.. image:: https://buildbot.gridsync.io/png?builder=windows
    :target: https://buildbot.gridsync.io/builders/windows


Gridsync aims to provide a cross-platform, graphical user interface for `Tahoe-LAFS`_, the Least Authority File Store. It is intended to simplify the configuration and management of locally-running Tahoe-LAFS gateways and to provide user-friendly mechanisms for seamlessly backing up local files, synchronizing directories between devices, and sharing files and storage resources with other users across all major desktop platforms (GNU/Linux, macOS, and Windows). More generally, Gridsync aims to duplicate most of the core functionality provided by other, proprietary "cloud" backup/synchronization services and utilities (such as Dropbox and BitTorrent Sync) but without demanding any sacrifice of the user's privacy or freedom -- and without requiring usage or knowledge of the command line. Accordingly, Gridsync is developed under the principle that secure file storage and backups should be freely available to everyone, without exception, without added barriers, and regardless of one's operating system choice.

.. _Tahoe-LAFS: https://tahoe-lafs.org


Why Gridsync?
-------------

Tahoe-LAFS already provides a number of highly desirable properties for file-storage: it is secure, decentralized, highly robust, free (as in both beer and speech), stable and mature, and written by a group of very talented developers. Unfortunately -- and despite all of its technical merits -- Tahoe-LAFS has a number of persistent usability issues which steepen its learning curve: its installation requires manual compilation from source on Windows and macOS, its configuration consists in hand-editing text files, its primary interface requires heavy command line usage, and many of its fundamental concepts (e.g., "dircap", "servers-of-happiness") are opaque to new users or otherwise demand additional reading of the project's extensive documentation. Accordingly, Tahoe-LAFS' userbase consists primarily in seasoned developers and system administrators; non-technical users are naturally excluded from enjoying Tahoe-LAFS' aforementioned advantages.

The Gridsync project intends to overcome some of Tahoe-LAFS' usability barriers by means of following features:

* Native, "batteries included" packaging on macOS and Windows -- Gridsync bundles will include Tahoe-LAFS and all required dependencies for a frictionless installation experience; no python installation or manual compilation is required
* A graphical user interface for managing all primary Tahoe-LAFS gateway functionality (e.g., starting, stopping, configuring nodes) -- the user will never have to edit a text file by hand or touch the command line
* Native look and feel -- Gridsync uses the Qt application framework, emulating native widgets on all target platforms; the user can expect Gridsync to behave like any other desktop application.
* Automated bi-directional file synchronization -- Gridsync will monitor local and remote directories, seamlessly storing or retrieving new versions of files as they appear (using Tahoe-LAFS' ``tahoe backup`` command and/or its forthcoming "Magic Folder" utility [*]_ ).
* Status indicators and desktop notifications -- the user will know, at a glance, when files are being uploaded or downloaded (via system tray icon animations) and will optionally receive notifications (via DBus on GNU/Linux, Notification Center on macOS, etc.) when operations have completed.
* Easy sharing -- Gridsync will use the `magic-wormhole`_ library to provide human-pronounceable "invite codes" for joining storage grids and sharing folders and files with other users.

.. _magic-wormhole: http://magic-wormhole.io

.. [*] Tahoe-LAFS' "Magic Folder" functionality does not (yet) support macOS or other BSD-based operating systems and is presently marked as experimental.


Screenshots:
------------

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/invite.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/branding.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/syncing.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/notification.png


Installation and running (development builds):
----------------------------------------------

**Binary distributions:**

Unsigned binary distributions (currently tracking the `master` branch) are available for all three major desktop platforms. These packages, however, should not be considered trustworthy or reliable in any way and are intended for testing purposes only. Please excercise appropriate caution when using these files (ideally by downloading and running them inside a disposable virtual machine).

For GNU/Linux (tested on Debian 8 and Fedora 23):

1. Download `Gridsync-Linux.tar.gz`_
2. Extract the enclosed "Gridsync" directory anywhere (``tar xvf Gridsync-Linux.tar.gz``)
3. Run the contained ``gridsync`` binary

.. _Gridsync-Linux.tar.gz: https://buildbot.gridsync.io/artifacts/Gridsync-Linux.tar.gz

For macOS [*]_ :

1. Download `Gridsync-Mac.dmg`_
2. Drag the enclosed "Gridsync.app" bundle anywhere (e.g., ``~/Applications``)
3. Double-click ``Gridsync.app``

.. _Gridsync-Mac.dmg: https://buildbot.gridsync.io/artifacts/Gridsync-Mac.dmg

For Windows (tested on Windows 7 SP1, Windows 8.1, and Windows 10):

1. Download `Gridsync-Windows.zip`_
2. Extract the enclosed "Gridsync" folder anywhere
3. Run the contained ``Gridsync.exe`` binary

.. _Gridsync-Windows.zip: https://buildbot.gridsync.io/artifacts/Gridsync-Windows.zip


.. [*] macOS users may need to explicitly allow third-party apps in order to use Gridsync ("System Preferences" -> "Security & Privacy" -> "General" -> "Allow apps downloaded from:" -> "Anywhere").


**From source:**

Because Tahoe-LAFS has not yet been ported to python3, and because some GNU/Linux distributions might contain especially old packages for some dependencies (including Tahoe-LAFS and Qt5), it is recommended to install and run Tahoe-LAFS and Gridsync inside their own virtual environments using updated dependencies from PyPI (ideally with hashes verified). Installing and running Gridsync with python3.5 (instead of python2) furthermore avoids having to install Qt5/PyQt5 manually (since PyQt5 wheels containing Qt5 are now available on PyPI for python 3.5+).

The following series of steps (run from the top level of the Gridsync source tree) should work on most Debian-based GNU/Linux distributions:

.. code-block:: shell-session

    sudo apt-get install virtualenv build-essential python-dev libssl-dev libffi-dev python3.5-dev
    virtualenv --python=python2 ./venv2
    ./venv2/bin/pip install --upgrade setuptools pip
    ./venv2/bin/pip install tahoe-lafs
    virtualenv --python=python3.5 ./venv3
    ./venv3/bin/pip install --upgrade setuptools pip
    ./venv3/bin/pip install -r requirements/requirements-hashes.txt
    ./venv3/bin/pip install .
    PATH=$PATH:./venv2/bin ./venv3/bin/gridsync


Users of other distributions and operating systems should modify the above steps as required (for example, by installing Xcode on macOS in addition to python -- or the dependencies listed at the top of `make.bat`_ in the case of Windows).

.. _make.bat: https://github.com/gridsync/gridsync/blob/master/make.bat


Known issues and limitations:
-----------------------------

While Gridsync ultimately aims to provide an easy-to-use frontend for users of Tahoe-LAFS, at present, its interface only supports a very limited subset of Tahoe-LAFS's underlying features and potential use-cases (namely, it provides simplified means for joining storage grids, creating and removing personal "magic-folders," and receiving status updates and notifications pertaining to those processes as they occur). Accordingly, users should not (yet) expect Gridsync to provide a complete backup solution or to serve as a stand-in replacement for other tools with robust sharing and collaboration capabilities.

In addition, it should be noted that Tahoe-LAFS's "magic-folder" functionality itself is currently considered "experimental" and has a number of known issues and bugs that users should be aware of. For example, magic-folders currently `do not preserve metadata`_ (such as file modification times), will often `overwrite local file permissions`_, and have been known to `create duplicate copies of local files`_. A more complete listing of upstream issues relating to Tahoe-LAFS's magic-folders can be found on the official `Tahoe-LAFS project website`_.

.. _do not preserve metadata: https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2882
.. _overwrite local file permissions: https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2881
.. _create duplicate copies of local files: https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2880
.. _Tahoe-LAFS project website: https://tahoe-lafs.org/trac/tahoe-lafs/search?q=magic-folder&noquickjump=1&ticket=on


Contributing:
-------------

Contributions of any sort (e.g., suggestions, criticisms, bug reports, pull requests) are more than welcome. Any persons interested in aiding the development of Gridsync are encouraged to do so by opening a `GitHub Issue`_ or by contacting its primary developer: `chris@gridsync.io`_

.. _GitHub Issue: https://github.com/gridsync/gridsync/issues
.. _chris@gridsync.io: mailto:chris@gridsync.io

License:
--------

Copyright (C) 2015-2017  Christopher R. Wood

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.


Sponsors:
---------

The ongoing development of this project is made possible by the generous sponsorships provided by `Least Authority`_ and `UXFund`_.

.. _Least Authority: https://leastauthority.com/
.. _UXFund: https://usable.tools/uxfund.html
