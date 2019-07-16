# Changelog

## Unreleased
### Added
- Basic support for fetching and displaying "newscap" messages; see `docs/proposed/newscaps.md` (Issue #184; PR #192, #211)
- Notification "badges" will now be displayed over the system tray icon to indicate unread newscap messages (Issue #226, PR #227)
- The application menu -- normally accessible by right-clicking the system tray icon -- is now also always accessible via a button in the status panel (Issue #201, PR #202)
- Clicking a desktop notification on Windows will now activate the main window (Issue #209; PR #210)
- macOS Mojave's "dark mode" is now supported (Issue #213, PR #217)
- Added support for "cross-compiling" Gridsync binaries via Vagrant/VirtualBox; see `README.rst` (Issue #230, PR #231)

### Changed
- Binary distributions of Gridsync will now ship with Python version 3.7 (Issue #175; PR #187)
- The "remove" folder action and subsequent confirmation dialog have been re-framed/updated to "stop syncing" instead. In addition, removing/stopping a folder will now unlink it from the user's rootcap/Recovery Key by default (i.e., unless the user checks the accompanying checkbox to "keep a backup copy of this folder on $GridName") (Issue #183, PR #190)
- Various scripts, configurations, and operations relating to the Gridsync CI/testing/build process have been updated and improved, slightly reducing at least one developer's growing frustrations with Travis-CI and buildbot (PR #188)
- Twisted's `reactor.spawnProcess` will now be used for running `tahoe` subprocesses on Windows, instead of threaded `subprocess.Popen` calls (Issue #176, PR #195)
- Gridsync binary distributions will now use and ship with (Py)Qt version 5.13 (Issue #228, PR #236)
- Due to ending upstream support and binary incompatibily with Qt 5.12, Debian 8 ("Jessie") and Ubuntu 14.04 ("Trusty Tahr") are no longer supported. Users running Debian 8 or Ubuntu 14.04 will need to upgrade their operating systems or build/install Gridsync from source (via `make`) (PR #196)
- High-DPI scaling (via Qt5's `AA_EnableHighDpiScaling` attribute) has been enabled on all platforms/environments (except for Qubes-OS and MATE -- see #204). In addition, font- and pixmap-scaling has been improved (Issue #193, #198, #232; PR #199, #203, #204, #233)
- The "Open Gridsync" menu action will now also un-minimize and re-focus the window in the event that it is already open (Issue #205; PR #206)
- Desktop notifications for connection/disconnection events are now disabled by default (Issue #218, PR #219)

### Fixed
- "Cheat codes" that correspond to non-existent configuration files are now rejected as invalid (Issue #185; PR #186)
- `libstdc++` has been excluded from Linux PyInstaller bundles, preventing a crash that coincided with opening a native file-chooser dialog on ArchLinux (Issue #189, PR #191)
- The "syncing" system tray icon animation will no longer continue to animate endlessly if a folder is removed/stopped before it finishes syncing (Issue #197, PR #200)
- Gridsync will now use atomic writes for all local configuration file updates (Issue #212, PR #214)
- The default Qt MainWindow toolbar context menu has been disabled, preventing the situation in which a user might accidentally hide the toolbar with no way of re-showing it until the application re-launches (Issue #215, PR #216)
- `SetupRunner.ensure_recovery` will now only be called when joining new grids, preventing an unnecessary upload from occurring -- and sometimes failing, due to a race-condition  -- when trying to join a grid that was already joined (Issue #220, PR #221)
- The unused "?"/"What's This" QDialog button (enabled by Qt on Windows by default) has been removed (Issue #222, PR #223)
- Double-clicking a newly-joined folder to open it before the tahoe daemon has finished (re)starting will no longer result in a crash (Issue #224, PR #225, #229)
- Modifying the application name via `config.txt` will no longer cause the `config_dir` tests to fail erroneously (Issue #234, PR #235)

## 0.4.2 - 2019-04-06
### Added
- An interface for viewing and exporting debugging information/logs for Gridsync and its underlying Tahoe-LAFS processes has been added (accessible via the system tray menu under "Help" -> "Export Debug Information...") (Issue #173, #168; PR #174, #179) -- thanks to @exarkun for providing the Tahoe-side functionality to make this happen! :)

### Changed
- "Sharing"-related actions have been reframed considerably throughout the interface in order to more precisely convey the underlying functionality of the application -- i.e., that "sharing" entails the _creating_ or _entering_ _invite codes_ and that these invite codes are created/entered on _devices_ (rather than "shared" with "persons") (Issue #139, PR #166). In particular:
    - The "Enter Code" button on the MainWindow toolbar has been replaced with an "Invites" button (offering "Enter Invite Code" and "Create Invite Code" sub-actions), while the vague/ambiguous "Share" button has been removed completely
    - The top-level "Share" action in the right-click/context menu has been replaced with a more accurate "Sync with Device" -> "Create Invite Code" menu/action hierarchy
    - The "person" overlay/emblem (which appeared over icons for "shared" folders) has been replaced with a "laptop" overlay/emblem instead
    - The tooltip for "shared" folders has removed references to "persons"
- The "Export Recovery Key" action in the systray menu has been removed (since it is already available on the MainWindow toolbar) (PR #166)
- The "Preferences" action/button on the MainWindow toolbar has been moved to the system tray menu (PR #166)
- The History View toggle has been moved to the right-hand side of the grid pulldown/combobox (PR #166)
- Binary distributions of Gridsync will now include a much newer build/version of Tahoe-LAFS that includes upstream support for magic-folders on macOS (Tahoe ticket [1432](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/1432)) and other bug-fixes (Tahoe tickets [2965](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2965), [2997](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2997),  [3006](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/3006), [3017](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/3017)) -- thanks (again) @exarkun! :)
- Numerous logging messages have been updated to remove or redact potentially sensitive information such as folder names, file/directory paths, Tahoe-LAFS storage fURLs, and capabilities (Issue #61; PR #179, #181)

### Fixed
- Gridsync will now perform an additional check to ensure that enough storage servers are available before attempting to make a directory, link/unlink a capability, or upload/download a file (effectively "pausing" or delaying these operations until a sufficient number of connections have been established) in order to reduce the likelihood of connection-related errors/failures when initially joining a storage grid
- Gridsync should no longer open a connection to the wormhole relay/rendezvous server when first initializing a `Wormhole` object, preventing the situation in which a second "clearnet" connection would idly persist (but remain unused) after adding a new connection via magic-wormhole over Tor -- big thanks to @abmoka (82b13dff1b5fee62eaaff6d483da66bb792a73cd @ Akomba Labs) for reporting this issue! (Issue #169, PR #171)
- When running under a PyInstaller/frozen python interpreter, Gridsync/`xdg-open` should now correctly launch the user's browser when clicking links to URLs within the application (Issue #177, PR #180)
- On desktop environments that do not support a system tray, the system tray menu will be accessible instead from the bottom-right corner of the status panel (Issue #178; PR #182)

## 0.4.1 - 2019-03-12
### Added
- A rudimentary, text-based progress-indicator has been implemented, displaying the overall percentage of transferred/remaining bytes during folder-syncing operations (shown under the "Status" column of the folder-manager) (Issue #132, PR #142)
- `config.txt` now accepts a `logo_icon` application setting, allowing whitelabel/rebranded distributions to display a larger logo on the initial welcome screen (in place of the default application icon + description combination) (PR #150)
- `config.txt` now also accepts an optional `[message]` section with `title`, `text`, and (icon) `type` settings, allowing whitelabel/rebranded distributions to display a custom message to users upon starting the application (PR #161, #162)

### Changed
- The Gridsync project no longer depends on [Travis-CI](https://travis-ci.org/) or [AppVeyor](https://www.appveyor.com/) for build-deployment and will now instead use dedicated virtual machines running on dedicated hardware for releases (PR #165). Currently, the following operating system versions should be considered supported (64-bit only):
    - For GNU/Linux: glibc 2.17 and above -- including Debian 8+, Ubuntu 14.04+, CentOS 7+, and Fedora 29+
    - For macOS: macOS 10.12 "Sierra" and above
    - For Windows: Windows Server 2012R2, Windows 7 SP1, Windows 8.1, and Windows 10
- The interprocess mutex (used to prevent multiple instances of Gridsync from running at the same time) has been changed from a listening TCP port to a filesystem lock (using `fcntl` on UNIX-based systems), preventing false "Gridsync is already running" errors under some macOS 10.14 environments (Issue #138, PR #141)
- The Windows executable installer will now prompt the user whether install the application "for me only" or "for all users"; it is now possible to install Gridsync without requiring an administrator password (Issue #152, PR #153)
- The unnecessary Tcl/Tk dependency inserted by PyInstaller has been removed from Tahoe-LAFS bundles on Windows, reducing the resultant application filesize by about 10 MB (PR #154)
- The "Open Gridsync" system tray menu action is now always enabled but now will show/raise the "welcome" window in the event that no storage grids have been joined (Issue #147, PR #155)
- PyInstaller/binary bundles will now always use the Tahoe-LAFS executable included inside the application directory (as opposed to selecting a `tahoe` executable from the user's `PATH`) (PR #158)
- Gridsync will now use the Tahoe-LAFS web API directly when adding/creating new folders (instead of shelling out to the `tahoe` python CLI), resulting in significantly faster initial magic-folder creates and facilitating better error-handling (Issue #145, PR #160)
- If a magic-folder fails to get added/created for any reason, Gridsync will automatically retry that operation after a 3 second delay. It will only re-try once, however (and will display an error message in the event of a second failure) (Issue #145, PR #160)
- A warning/confirmation message-box will be displayed to the user in the event that they try to exit the application while a newly-added folder is still in the process of being created or if any existing folders are currently syncing (Issue #145, PR #160)
- The `[help]` section of `config.txt` is now optional; the "Browse Documentation" and "Report Issue" actions in the systray help submenu will now only appear if `docs_url` and `issues_url` respectively have been set (PR #164) 

### Fixed
- Gridsync will now display an error message -- rather than crash -- in the (rare) event that a user tries to restore a folder without actually possessing the correct capabilities to do so (Issue #143, PR #144)
- The desktop environment-specific file-manager should now properly launch when opening a folder under a PyInstaller build on Linux (Issue #146, PR #148)
- The environment-specified font should now correctly load when running a PyInstaller build on Linux (Issue #84)
- Gridsync will now refrain from trying to restart a tahoe client if that client is already in the proccess of stopping or starting, preventing needless tahoe restarts when adding new folders in quick succession (Issue #149, PR #151)
- On Windows, the application icon should no longer persist in the system tray after the application has exited (Issue #156, PR #157)
- The logic surrounding `tahoe` daemon restarts after adding folders has been improved; Gridsync will now wait until all known/queued linking events have completed before proceeding with a `tahoe stop` and will not attempt to restart unless at least one folder has been added/created successfully (Issue #145, PR #160)
- In the event that a magic-folder cannot be added/created, it will be removed immediately from the folder view/model in the UI (after displaying an error message); failed folders should no longer linger or appear stuck in a "Loading..." state and/or need to be removed manually (PR #160)
- A rare Qt-related crash (caused by Gridsync trying to update the mtime or size for a folder that has recently been removed) has been fixed (PR #160)
- In hopes of fighting off any ["Zombie Dragons"](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2996), Gridsync will now restart the `tahoe` daemon after successfully leaving a magic-folder (PR #163)
- When permanently removing one or more magic-folders, Gridsync will now wait until all unlink operations have completed before rescanning the rootcap, preventing the situation in which a folder might re-appear in the UI as "Remotely stored" despite having just been removed (PR #163)

## 0.4.0 - 2019-01-11
### Added
- Tor integration (**EXPERIMENTAL**)
    - Gridsync can now optionally tunnel outgoing connections through the Tor anonymity network; see [`docs/tor-integration.md`](https://github.com/gridsync/gridsync/blob/master/docs/tor-integration.md) (Issue #64, Issue #99, PR #82, PR #127, PR #129)
- Application preferences are now also accessible from the initial welcome screen
- A "Restore from Recovery Key" link/option is now available directly from the initial welcome screen (Issue #60)
- An Inno Setup Windows executable installer ("Gridsync-setup.exe") is now provided (Issue #35)
- Backspace/Delete key-presses can now be used to remove folders
- An "action" button/column has been added for each folder/row, making folder-specific actions accessible via left-click (Issue #89)
- A (very) basic "About"/version dialog has been added, accessible via the systray menu
- A "history" view has been added, displaying a chronological record of recent changes made to magic-folders and enabling per-file actions (Issue #92, PR #116, PR #124)
- Support for high-DPI "retina" displays has been enabled for macOS ".app" bundles (PR #116)
- In-app "help" buttons/dialogs have been added to invite-code widgets, providing additional information about "invite codes" and "Tor" (PR #129)
- macOS binary releases are now certified by Apple (signed by "Developer ID Application: Christopher Wood (6X3QVDWX28)"); users should no longer receive "unidentified developer" warnings from Gatekeeper when launching Gridsync (Issue #20)

### Changed
- Due to upstream changes/deprecations with the Homebrew package manager and Qt5, the minimum "officially" supported version of macOS for Gridsync binary distributions has been increased from 10.10 ("Yosemite") to 10.11 ("El Capitan"). For users who have not yet upgraded or who are still using older hardware, however, a ["legacy"](https://github.com/gridsync/gridsync/releases) distribution of Gridsync has been provided (based off Qt 5.8 and tested to run on 2009-era hardware with versions of macOS as old as 10.9) (Issue #110)
- The version of Tahoe-LAFS included in Windows and Linux binary distrubutions has been upgraded to 1.13.0 (PR #108)
- macOS binary distributions will now include a more recent (but still unreleased) version of Tahoe-LAFS with numerous magic-folder-related bug-fixes and improvements -- thanks @vu3rdd!
- Gridsync will now run as an "agent" application on macOS, accessible from the menu bar but no longer appearing in the Dock (Issue #86, PR #112, PR #114)
- A "person" overlay/embled will now be displayed over the icons of shared folders (PR #129, PR #133)
- Failure to decrypt a recovery key no longer requires re-importing the file to try again (Issue #60)
- Font sizes have been increased on macOS to match the equivalent weights on most Linux and Windows environments
- The dynamic action button inside invite code fields will now also update on window-enter cursor events (allowing, e.g., the "paste" button to become conveniently activated after copying an invite code to the clipboard from another window)
- The main/status window's title will now include the name of the currently-active grid
- The Preferences pane has been detached into a floating Preferences window with per-section "tabs" (Issue #117, PR #119)
- The MainWindow toolbar has been updated; text labels have been added beneath buttons and some actions have been re-organized (Issue #106, PR #120)
- The MainWindow status bar has been replaced with a "status panel", showing grid-related status information in a more compact manner (PR #116, PR #123)
- Various misc. UI elements (widgets, margins, fonts, etc.) have been adjusted on macOS and Windows to better match the underlying desktop environment (PR #125, PR #129)

### Removed
- The "default" provider section of `config.txt` has been removed; organizations wishing to deploy a modified Gridsync client with pre-configured settings are encouraged to use a ["cheat code"](https://github.com/gridsync/gridsync/blob/master/docs/cheat-codes.md) instead
- The "Import from Recovery Key" option has been removed from the manual configuration screen (since this functionality is now available from the welcome screen)
- The "green lock" folder icon overlay has been removed (Issue #121, PR #122)

### Fixed
- `tahoe.select_executable()` will now use an empty nodedir when checking tahoe instances for multi-magic-folder support (preventing potential inaccuracies caused, e.g., by a pre-existing/misconfigured `$HOME/.tahoe` nodedir)
- Tahoe subclients created from older versions of Tahoe-LAFS that only support "legacy" magic-folders will now correctly inherit the parent client's `servers.yaml` settings upon creation.
- The "Open Gridsync" systray menu action will correctly remain disabled until at least one grid has been succesfully joined
- Users will no longer be prompted to export a Recovery Key after restoring a connection from one
- Empty folders will no longer appear stuck in a "Loading" state (Issue #73)
- Gridsync will now shutdown more gracefully, avoiding qt5reactor-related hangs when exiting
- Subdirectory objects are now ignored when parsing magic-folders (avoiding [Tahoe-LAFS bug #2924](https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2924)) (PR #115)
- Newly joined grids will become available/selected immediately from the main window comboxbox (PR #126, PR #129)

## 0.3.2 - 2018-04-17
### Added
- Support for introducerless connections; Gridsync can now write storage fURLs received through invite messages directly to `$nodedir/private/servers.yaml`, bypassing the need to connect to an introducer node (Issue #65)
- Preliminary support for "cheat codes", allowing future users to enter a pre-given invite code to join a grid without the need to complete a full magic-wormhole exchange (Issue #54); see `docs/cheat-codes.md`

### Changed
- Magic-folder invites now use the Tahoe web API directly to create member subdirectories (as opposed to shelling out to `tahoe magic-folde invite`) and will do so concurrently in the event of "batched" invites, resulting in significantly faster overall invite code creation when sharing folders (Issue #57)
- Gridsync will now prompt users for a grid name in the event that one is not provided inside an invite message

### Fixed
- Rare crashes caused by the successive emitting of certain `pyqtSignal`s
- Overflow in "size" column caused by PyQt's C++ types (Issue #78) -- thanks @yegortimoshenko!

## 0.3.1 - 2018-03-29
### Added
- "Start minimized" option to Preferences pane
- "Start automatically on login" option to Preferences pane (Issue #66)
- Error message when trying to join an already-existing grid (Issue #68)

### Changed
- The application will no longer start in a "minimized" state by default (Issue #69)
- Updated qt5reactor to wake up less often, reducing idle CPU consumption -- thanks @exarkun!

### Fixed
- "Last modified" time will no longer update until after the first remote scan has completed, thereby preventing misleading mtimes (e.g., "48 years ago") from being displayed briefly on start (Issue #63).
- Invites received through the "Add Folder" button will no longer appear to "hang" when receiving an invite that does not contain a magic-folder join-code (Issue #67)
- Setup will now only prompt for a grid-rename if the introducer fURL received through the invite actually differs from that of the conflicting target nodedir (Issue #68)
- Setup will now actually try to fetch icon URLs provided inside invite messages

## 0.3.0 - 2018-03-10
### Added
- New "Recovery Key" system
    - Users can now export (and optionally encrypt) a "[Recovery Key](https://github.com/gridsync/gridsync/blob/master/docs/recovery-keys.md)" -- a small file (containing grid connection settings and a "rootcap") sufficient for restoring access to previously added/joined folders (see [`docs/recovery-keys.md`](https://github.com/gridsync/gridsync/blob/master/docs/recovery-keys.md)).
- Folder-sharing
    - Users can now share/sync added folders among other users and devices using [invite codes](https://github.com/gridsync/gridsync/blob/master/docs/invite-codes.md). Newly joined folders will automatically synchronize between users/devices when updated, using Tahoe-LAFS' `magic-folder` feature.
- Multi-magic-folder support
    - Gridsync will now take advantage of Tahoe-LAFS' forthcoming "multi-magic-folder" feature (of adding/joining multiple magic-folders through a single `tahoe` client instance) resulting in significant resource savings. When running with a compatible `tahoe` client (now included in Linux and Windows binary distributions), Gridsync will automatically migrate its own "legacy" multi-nodedir configuration format to use the new single-nodedir format.
- Numerous new misc. UI elements
    - Including additional toolbar icons/actions (for, e.g., adding new folders, exporting a Recovery Key), expanded status information (showing, e.g., number of connected storage nodes, amount of space remaining, "last modified" times, whether folders are "stored remotely" vs. active locally, etc.), and error messages (when trying to, e.g.,add individual files, overwrite already-existing folders, etc.).

### Changed
- The magic-wormhole/"invite code" `appid` has been changed (from `tahoe-lafs.org/tahoe-lafs/v1` to `tahoe-lafs.org/invite`) in order to be compatible with Tahoe-LAFS' forthcoming [`tahoe invite`](https://tahoe-lafs.readthedocs.io/en/latest/magic-wormhole-invites.html) feature; **Gridsync 0.2 users will need to upgrade to version 0.3 in order to send/receive grid invites to/from version 0.3 users.**
- Updated various UI elements (icons, text labels, etc.) to be more clear
- Upgraded bundled Qt libraries to version 5.10.1
- Upgraded bundled Python interpreter to version 3.6
- Upgraded bundled Tahoe-LAFS binary to [1.12.1.post198](https://github.com/tahoe-lafs/tahoe-lafs/tree/0442b49846a1dd71d43e59b600eff973684eb4e4) for various magic-folder fixes (Linux and Windows only)
- Dropped Python 2 support

### Fixed
- Removed potentially-conflicting bundled libraries from Linux binary distributions (Issues #43, #47)
- Numerous other minor UI-related bugs, performance issues, misc. bugs, etc.

## 0.2.0 - 2017-08-10
- Added support for device-pairing/grid-sharing via magic-wormhole/invite codes
- Added "Preferences" pane with user-configurable desktop notifications
- Updated drag-and-drop UI with new graphics/labels and accessibility improvements
- Numerous minor tweaks and fixes

## 0.1.0 - 2017-07-14
- Updated magic-wormhole/invite protocol to be compatible with forthcoming(?) `tahoe invite` command
- Added support for `icon_url` key in invite JSON response and pre-bundled image files (currently, "Least Authority S4" only)
- Fixed display/update of "Last sync" value in status window for in-progress magic-folder sync operations
- Numerous documentation updates and additions (README; verifying-signatures, invite-codes)
- Other misc. cleanups and bug fixes

## 0.0.5 - 2017-06-29

## 0.0.4 - 2017-05-29

## 0.0.3 - 2017-05-24

## 0.0.2 - 2017-05-23

## 0.0.1 - 2017-05-23
