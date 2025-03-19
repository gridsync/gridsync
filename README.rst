========
Gridsync
========

.. image:: https://github.com/gridsync/gridsync/workflows/CI/badge.svg
    :target: https://github.com/gridsync/gridsync/actions/


Gridsync aims to provide a cross-platform, graphical user interface for `Tahoe-LAFS`_, the Least Authority File Store. It is intended to simplify the Tahoe-LAFS installation and configuration process and ultimately provide user-friendly mechanisms for common use-cases like backing up local files, synchronizing directories between devices, and sharing files and folders with other users across all major desktop platforms (GNU/Linux, macOS, and Windows). More broadly, Gridsync aims to duplicate most of the core functionality provided by other, proprietary "cloud" backup and synchronization services and utilities (such as Dropbox and BitTorrent Sync) but without demanding any sacrifice of the user's privacy or freedom -- and without requiring usage or knowledge of the command line. Accordingly, Gridsync is developed with the goal in mind of making secure cloud storage freely available to everyone, without exception, without added barriers, and regardless of one's operating system choice.

.. _Tahoe-LAFS: https://tahoe-lafs.org


Why Gridsync?
-------------

Tahoe-LAFS already provides a number of highly desirable properties for secure file-storage: in addition to offering client-side encryption, it is decentralized, robust, free (as in both beer and speech), stable and mature, and written by a group of very talented developers. Unfortunately -- and despite all of its technical merits -- Tahoe-LAFS has a number of persistent usability issues which steepen its learning curve: its installation requires manual compilation from source on Windows and macOS, its configuration consists in hand-editing text files, its primary interface requires heavy command line usage, and many of its fundamental concepts (e.g., "dircap", "shares", "servers-of-happiness") are opaque to new users or otherwise demand additional reading of the project's extensive documentation. Accordingly, Tahoe-LAFS' userbase consists primarily in seasoned developers and system administrators; non-technical users are naturally excluded from enjoying Tahoe-LAFS's aforementioned advantages.

The Gridsync project intends to overcome some of Tahoe-LAFS's usability barriers by means of following features:

* "Batteries included" packaging -- Gridsync bundles will include Tahoe-LAFS and all required dependencies for a frictionless installation experience; no python installation or manual compilation is required.
* A graphical user interface for managing primary Tahoe-LAFS functionality (e.g., starting, stopping, configuring gateways) -- the user will never have to edit a text file by hand or touch the command line.
* "Native" look and feel -- Gridsync uses the Qt application framework, emulating native widgets on all target platforms; the user can expect Gridsync to behave like any other desktop application.
* Automated bi-directional file synchronization -- Gridsync will monitor local and remote directories, seamlessly storing or retrieving new versions of files as they appear (using `Magic-Folder`_).
* Status indicators -- the user will know, at a glance, the number of connected storage nodes, folder sizes and modification times, when folders are synchronizing, recently updated files, etc.
* Desktop integration -- Gridsync can (optionally) start automatically on login and provide desktop notifications when certain operations have completed.
* Easy sharing -- Gridsync uses the `magic-wormhole`_ library to provide human-pronounceable "`invite codes`_" for joining storage grids and sharing folders with other users.
* Simple recovery -- Gridsync's "`Recovery Key`_" subsystem allows connections and folders to be easily restored from a single file in the event of a disaster.
* `Tor support`_ (experimental) -- Gridsync can tunnel outgoing connections through the `Tor`_ anonymity network, concealing users' network location from storage service providers and each other.

.. _Magic-Folder: https://github.com/LeastAuthority/magic-folder
.. _magic-wormhole: http://magic-wormhole.io
.. _invite codes: https://github.com/gridsync/gridsync/blob/master/docs/invite-codes.md
.. _Recovery Key: https://github.com/gridsync/gridsync/blob/master/docs/recovery-keys.md
.. _Tor support: https://github.com/gridsync/gridsync/blob/master/docs/tor-integration.md
.. _Tor: https://torproject.org


Screenshots (latest release; running macOS 10.14 with dark mode enabled):
-------------------------------------------------------------------------

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/latest/02-drag-and-drop.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/latest/03-syncing.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/latest/04-history.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/latest/05-invite.png


Screenshots (previous releases; running GNU/Linux with Xfce 4):
---------------------------------------------------------------

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/welcome.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/connecting.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/dropzone.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/passphrase.gif

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/menu.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/share.png

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/notify.gif

.. image:: https://raw.githubusercontent.com/gridsync/gridsync/master/images/screenshots/old/history.png

Installation and running:
-------------------------

**Stable releases:**

Downloads for "stable" releases of Gridsync can be found on the project's `GitHub Releases page`_ and include pre-built/binary distrubitions for all three major desktop platforms that have been compiled inside dedicated virtual machines on dedicated hardware. Users wishing to install these packages are strongly urged to `verify their signatures`_ before running or, alternatively, to build/install Gridsync manually from source (see below).

.. _GitHub Releases page: https://github.com/gridsync/gridsync/releases
.. _verify their signatures: https://github.com/gridsync/gridsync/blob/master/docs/verifying-signatures.md

To install and run Gridsync on GNU/Linux (64-bit only; supporting glibc 2.17 and above -- including Ubuntu 20.04 LTS and later):

1. Download `Gridsync-Linux.AppImage`_ (and `verify`_ its signature)
2. Make the AppImage executable (``chmod +x Gridsync-Linux.AppImage``)
3. Run ``Gridsync-Linux.AppImage``

.. _Gridsync-Linux.AppImage: https://github.com/gridsync/gridsync/releases
.. _verify: https://github.com/gridsync/gridsync/blob/master/docs/verifying-signatures.md

To install and run Gridsync on macOS (64-bit only; supporting macOS 11 "Big Sur" and later):

1. Download `Gridsync-macOS.dmg`_ (and `verify`_ its signature)
2. Drag the enclosed "Gridsync.app" bundle anywhere (e.g., ``~/Applications``)
3. Double-click ``Gridsync.app``

.. _Gridsync-macOS.dmg: https://github.com/gridsync/gridsync/releases
.. _verify: https://github.com/gridsync/gridsync/blob/master/docs/verifying-signatures.md

To install and run Gridsync on Windows (64-bit only; supporting Windows 10 and Windows 11):

1. Download `Gridsync-Windows-setup.exe`_ (and `verify`_ its signature)
2. Run the executable installer and follow/complete the setup wizard
3. Select "Launch Gridsync" when installation is finished

.. _Gridsync-Windows-setup.exe: https://github.com/gridsync/gridsync/releases
.. _verify: https://github.com/gridsync/gridsync/blob/master/docs/verifying-signatures.md


**From source:**

The project `Makefile`_ (or `make.bat`_ file on Windows) references the various scripts and commands necessary for building Gridsync from source. For most users with Python already installed, building the application should simply be a matter of issuing a `make` command at the top-level of the source tree:

.. code-block:: shell-session

    make
 

This will create a standalone executable distribution of Gridsync with all of its dependencies included (including a "frozen" python interpreter and Tahoe-LAFS, using `PyInstaller`_), placing the resultant files/installers in the `dist/` subdirectory. The Gridsync build process is `reproducible`_ such that, given the same set of build inputs (i.e., a particular revision of the source code), the resultant build output(s) (i.e., the application binaries) will always be bit-for-bit identical. Should any errors arise regarding missing dependencies, a `provision_devtools.sh`_ script (or `provision_devtools.bat`_ on Windows) is provided to download and install all of the core dependencies needed to build Gridsync on most supported operating systems.

.. _Makefile: https://github.com/gridsync/gridsync/blob/master/Makefile
.. _make.bat: https://github.com/gridsync/gridsync/blob/master/make.bat
.. _PyInstaller: http://www.pyinstaller.org/
.. _reproducible: https://reproducible-builds.org/
.. _provision_devtools.sh: https://github.com/gridsync/gridsync/blob/master/scripts/provision_devtools.sh
.. _provision_devtools.bat: https://github.com/gridsync/gridsync/blob/master/scripts/provision_devtools.bat

Note, however, that PyInstaller-generated binaries are typically `not backward-compatible`_; a PyInstaller executable that was built on a newer GNU/Linux distribution, for example (i.e., with a more recent version of `glibc`) will not run on older distributions. Accordingly, if you intend to distribute Gridsync binaries for use on a wide range operating system versions, it is recommended that you build the application on as old of a system as is reasonable for a given platform (i.e., one which can build and run Gridsync but which still receives security updates). Presently, CentOS 7, macOS "Mojave" (10.14), and Windows 10 arguably constitute the most suitable candidates for GNU/Linux, macOS, and Windows build systems respectively (insofar as binaries generated on these systems will be forward-compatible with all others in that platform-category that are still supported upstream).

.. _not backward-compatible: https://pyinstaller.readthedocs.io/en/latest/usage.html#platform-specific-notes

To help facilitate the testing, building, and distribution of forward-compatible binaries -- as well as to enable a crude form of "cross-compilation" -- a custom `Vagrantfile`_ has been provided inside the Gridsync source tree; users or developers with `Vagrant`_ and `VirtualBox`_ installed [*]_ can automatically provision a complete Gridsync build environment that produces forward-compatible binaries via the following commands:

.. code-block:: shell-session

    make vagrant-build-linux
    make vagrant-build-macos
    make vagrant-build-windows


These will download and configure a suitable virtual machine for the target platform (from the `public Vagrant Boxes catalog`_), provision it with all required dependencies (such compilers/SDKs, python interpreters, X11 libraries, etc.), copy the Gridsync source code into the target VM, run the Gridsync test suite, and compile a final PyInstaller-generated binary package suitable for distribution (the result of which can be found in the `~/gridsync/dist` directory of the guest VM).

.. _Vagrantfile: https://github.com/gridsync/gridsync/tree/master/Vagrantfile
.. _Vagrant: https://www.vagrantup.com/
.. _VirtualBox: https://www.virtualbox.org/
.. _public Vagrant Boxes catalog: https://app.vagrantup.com/boxes/search

.. [*] Note that in order to get Vagrant/VirtualBox working properly, users of GNU/Linux may need to add the current user's name to the local "vboxusers" group, while users experiencing issues with Windows guests may need to install some combination of the `winrm`, `winrm-fs`, or `winrm-elevated` Vagrant plugins (via the `vagrant plugin install winrm winrm-fs winrm-elevated` command). For further assistance with installing, configuring, or using Vagrant and/or VirtualBox on your system, please consult the appropriate upstream documentation and/or help forums. In addition, please note that Gridsync project can make no guarantees about the security or safety of public Vagrant "Boxes"; please exercise appropriate caution when relying upon third-party software.


Alternatively, users with `docker` installed can use the CentOS 7-based `gridsync-builder`_ image to build equivalent backward-compatible binaries without the addded overhead of Vagrant and VirtualBox:

.. code-block:: shell-session

    make in-container


.. _gridsync-builder: https://hub.docker.com/repository/docker/gridsync/gridsync-builder


Known issues and limitations:
-----------------------------

While Gridsync ultimately aims to provide an easy-to-use frontend for users of Tahoe-LAFS, at present, its interface only supports a very limited subset of Tahoe-LAFS's underlying features and potential use-cases (namely, it provides simplified means for joining storage grids, creating and sharing "magic-folders," and receiving status updates and notifications pertaining to those processes). Accordingly, users should not (yet) expect Gridsync to provide a complete backup solution or to serve as a stand-in replacement for other tools with robust sharing and collaboration capabilities. In addition, it should be noted that `Magic-Folder`_ is currently under heavy development and has a number of `known issues and limitations`_.

.. _Magic-Folder: https://github.com/LeastAuthority/magic-folder
.. _known issues and limitations: https://github.com/LeastAuthority/magic-folder/issues


Contributing:
-------------

Contributions of any sort (e.g., suggestions, criticisms, bug reports, pull requests) are welcome. Any persons interested in aiding the development of Gridsync are encouraged to do so by opening a `GitHub Issue`_ or by contacting its primary developer: `chris@gridsync.io`_

.. _GitHub Issue: https://github.com/gridsync/gridsync/issues
.. _chris@gridsync.io: mailto:chris@gridsync.io


License:
--------

Copyright (C) 2015-2025  Christopher R. Wood

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.


Sponsors:
---------

The ongoing development of this project has been made possible by the generous sponsorships and grants provided by `Least Authority`_ (2016-), `Internews/UXFund`_ (2017), and `Open Technology Fund`_ (2019-2020).

.. _Least Authority: https://leastauthority.com/
.. _Internews/UXFund: https://usable.tools/blog/2016-12-28-uxfund-results/
.. _Open Technology Fund: https://leastauthority.com/blog/secure-file-storage-tools-human-rights-defenders/
