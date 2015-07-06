========
UX notes
========

"First time" run UX sketch/outline:
-----------------------------------

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


On systray icons:
-----------------

The Gridsync system tray icon will animate during synchronization activity, indicating to the user that upload/download tasks are in progress. More specifically, the icon elements will rotate/animate in a clockwise direction when a Tahoe ``backup`` process is running, and counter-clockwise when restoring from or rolling back to a previous snapshot. In this regard, the icon animation is analogous to the motions of an analog clock; clockwise motions are intended to indicate that the user's files are being brought "up to date," while counter-clockwise motions are intended to indicate that the user is "going back in time" to a previous state.


On desktop notifications:
-------------------------

Desktop notifications shall be used sparingly and for tasks which are seldom occuring (e.g., syncing a new sync target, restoring a directory from a previous state, receiving a link from a friend).

