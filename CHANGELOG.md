# Changelog

## Unreleased
### Added
- Added support for new Magic-Folder "[invites](https://github.com/LeastAuthority/magic-folder/pull/682)" functionality (Issue #598; PR #611)
- Added support for Python 3.11 (Issue #518; PR #620)

### Changed
- Use of the `pytest-xvfb` plugin has been replaced with manual `xvfb-run` calls (Issue #591; PR #593) -- thanks @exarkun!
- HTML/CSS is now stripped from error messages surfaced by the Tahoe-LAFS web API (Issue #572; PR #592)
- Gridsync now uses the new Magic-Folder "events" API for displaying most (but not all) folders-related information instead of busily polling and comparing state across time (Issue #615; PR #634)
- Replaced `flake8` with `ruff` in the tox "lint" testenv (PR #624)
- Binary builds will now default to shipping with PyQt6 instead of PyQt5 (Issue #629; PR #630)
- The "Restore from Recovery Key" action is now always enabled/accessible from the main window's "Recovery" button (Issue #645; PR #646)

### Fixed
- Mypy will no longer warn about "types.py" shadowing the "types" library module (Issue #600; PR #601)
- Improved visibily of Magic-Folder invite-codes on macOS (Issue #626; PR #628)
- Fixed Wayland compatibility issue with Qt6-based AppImages (Issue #631; PRs #635, #638)
- Improved collection of "resources" files for PyInstaller bundles (Issue #636; PR #637)
- Fixed a crash triggered by launching the "About" dialog from the menu on Qt6 (Issue #640; PR #642)

### Removed
- Removed support for Python 3.9 (Issue #617; PR #618)


## 0.6.1 - 2022-10-14
### Added
- Added support for parsing/handling new Tahoe-LAFS and Magic-Folder "pidfiles" -- thanks @meejah! (PR #569)

### Changed
- Logs for Gridsync, Tahoe-LAFS, and Magic-Folder will now persist on disk instead of being buffered into memory (Issue #564; PR #570)
- PyInstaller has been updated to version 5.5 (Issue #561; PR #575)
- Gridsync will now apply new connection-related settings for grids that were previously joined via a "cheat code" (e.g., `0-hro-cloud`) during start-up, making it possible for some out-of-date grid-configurations (i.e., Least Authority's "HRO Cloud", as per #576) to be updated in conjunction with Gridsync itself (Issue #504; PR #578)

### Fixed
- The grid-configuration for Least Authority's "HRO Cloud" has been updated in response to a failing storage node, allowing users of the service to re-connect once again (PR #576)


## 0.6.0 - 2022-09-16
- No functional changes since 0.6.0rc1

## 0.6.0rc1 - 2022-09-14
### Added
- Added support for the new/standalone "[Magic-Folder](https://github.com/LeastAuthority/magic-folder)" application (Issue #290; PR #389)
- Errors contained in Magic-Folder "status" messages will now be surfaced to the user (Issue #390; PR #392)
- Added support for Tahoe-LAFS 1.16.0 (Issue #397; PR #398)
- Added "progress" indicators for Magic-Folder upload operations, displaying the number of completed vs. pending upload operations as a percentage (Issue #391; PR #399)
- Added tooling to facilitate updating/pinning ZKAPAuthorizer and Magic-Folder dependencies from non-release git revisions (PR #400) -- thanks @tomprince
- Added support for configuring the ZKAPAuthorizer lease crawler via grid JSON/settings (Issue #417; PR #418) -- thanks @exarkun!
- Configuration values declared by `config.txt` can now be overridden via environment variables (Issue #465; PR #466)
- Added preliminary support for alternative Qt APIs/libraries (by setting the `QT_API` environment variable to one of `pyqt5`, `pyqt6`, `pyside2`, or `pyside6` at build-time) (PR #467)
- Added support for Ubuntu 22.04 (PR #475)
- Added support for backing up and restoring the ZKAPAuthorizer database state via "v2" ZKAPAuthorizer endpoints (Issue #388; PRs #476, #478, #499) -- thanks @meejah!
- Added support for Python 3.10 (PR #495)
- Added a Nix-based development shell and related CI (PR #517) -- thanks @exarkun!
- Added some additional documentation for contributors (`CONTRIBUTING.rst`) (PR #547) -- thanks @meejah!

### Changed
- Binary distributions of Gridsync will now ship with Tahoe-LAFS version 1.17.1 and Magic-Folder 22.8.0 (PR #519)
- Added proper PyInstaller hooks for `twisted.plugins`, preventing the need to patch `allmydata.storage_client` at buildtime (PR #403) -- thanks @tomprince
- The Magic-Folder API port will now be determined by reading the newly-added `api_client_endpoint` file instead of parsing stdout (Issue #412; PR #416)
- Updated Recovery Key creation behavior/UX slightly (Issue #405; PR #420):
  - Users of ZKAPAuthorizer-enabled grids will now be prompted to create a Recovery Key immediately after successfully redeeming a batch of ZKAPs and creating a rootcap
  - Users who have not previously created a Recovery Key will now be prompted to do so (once per session)
  - Confirmation buttons ("Cancel", "Save...") have been added to the password dialog
  - Labels pertaining to Recovery Key-related actions have been updated throughout the UI:
    - "Export Recovery Key" has been updated/renamed to "Create Recovery Key"
    - "Import Recovery" has been updated/renamed to "Restore from Recovery Key"
- During start up, a "Loading..." label will now be shown under the Storage-Time view instead of temporarily displaying a storage-time balance of 0 (Issue #423; PR #424) -- thanks @exarkun!
- Bundled `tahoe` and `magic-folder` executables will now be prepended with the application name (e.g., "Gridsync-tahoe.exe" instead of "tahoe.exe") in order to more clearly distinguish process names managed by Gridsync (Issue #422; PR #426)
- The Storage-Time view now explicitly states (via a text label) that folders can be added while a voucher is being redeemed (Issue #427; PR #436)
- On Windows and macOS, the `certifi` package will now be used for TLS verification (Issues #441, #459; PRs #442, #460)
- The Tahoe-LAFS and Magic-Folder binaries included with Gridsync are now python3-only and utilize PyInstaller's "multipackage bundles" feature, drastically reducing the overall filesize of the Gridsync application bundle (Issue #432; PR #433)
- Users of ZKAPAuthorizer-enabled storage-grids will now receive a warning/confirmation dialog about lease-renewal upon exiting the application (PR #445)
- Debug log messages are now timezone-aware (Issue #447; PR #450)
- A warning/confirmation dialog will now be displayed describing the risks of sharing the same Recovery Key across multiple devices when restoring from a Recovery Key (Issue #448; PR #451)
- Gridsync will now automatically relaunch `tahoe` and `magic-folder` that were terminated by external factors (Issue #455; PR #470)
- It is now possible to add Magic-Folders for empty directories (PR #473)
- Updated the project `Vagrantfile`, adding virtual environments for newly-supported OS versions and removing unsupported ones (PR #485, #514, #515, #525, #533, #546)
- Refactored some code-paths relating to Recovery Key creation (PR #477) -- thanks @exarkun!
- Gridsync will now check processes names when making determinations about the staleness of existing processes/pidfiles (PR #492)
- Added type-annotations throughout the codebase (PR #468, #469, #477, #502)
- Updated the embedded grid-configuration for Least Authority's "HRO Cloud" (Issue #536; PRs #494, #537) -- thanks @jehadbaeth!
- Replaced usage of `inlineCallbacks`/`yield` with `async`/`await` syntax in several modules (Issues #520, #522, #523, #527; PRs #521, #524, #526, #529) -- thanks @exarkun!
- The Recovery Key subsystem has been changed in order to safeguard against simultaneous writers (Issue #449; PR #544):
  - Recovery Keys will now contain the read-only form of the rootcap capability (rather than the read-write capability)
  - Restoring from a Recovery Key will now always create a new (read-write) rootcap, copying the contents of the old/imported rootcap into it
  - *Note: This change -- along with PR #499 -- breaks compatibility with older Recovery Keys; users updating from an older version will need to re-create a Recovery Key*
- Websocket messages from the Magic-Folder "status" API will no longer be captured by the Gridsync debug log (Issue #549; PR #552)
- An error message will now be displayed when attempting to start Tahoe-LAFS with nodedir that contains incompatible/out-of-date configuration (PR #559)

### Fixed
- Fixed an uncaught `AttributeError` in `filter.py` (Issue #393; PR #394)
- Fixed an bug in which ZKAPAuthorizer's "allowed-public-keys" were being written to `servers.yaml` instead of `tahoe.cfg` (Issue #406; PR #407)
- Reduced CPU usage consumed by polling for storage server connections (Issue #414; PR #415) -- thanks @exarkun!
- Removing a folder will now update both the UI/FoldersView and underlying data-model(s) immediately, preventing the situation in which an error would occur when upon attempting to remove the same folder twice in rapid succession (Issue #437; PR #439)
- Additional checks are now performed at build-time to identify and prevent dependency-conflicts between Gridsync, Tahoe-LAFS, and Magic-Folder (Issue #434; PR #435)
- Several UI elements in the Storage-time view have been adjusted to prevent the labels in the chart legend from being truncated (Issue #453; PR #454)
- Improved error-handling when listing empty or unavailble Tahoe-LAFS directories (PR #464)
- Improved the efficiency and accuracy of updates to the "Status" column in the Folders view (Issue #461; PR #463)
- Fixed a crash caused by sending DBus desktop notifications on GNU/Linux systems that lack DBus (PR #474)
- Fixed an intermittently-failing test for `gridsync.Supervisor`'s restart behavior on Windows (PR #481)
- Fixed an uncaught `TypeError` caused by a missing positional argument (Issue #489; PR #490) -- thanks @makeworld-the-better-one!
- Fixed a crash caused by conflicting/incompatible pango libraries on ArchLinux (Issue #487; PR #488) -- thanks @makeworld-the-better-one!
- Added mitigations for a CPython/importlib bug triggered by `ResourceWarning`s on Windows (Issue #479; PRs #484, #498) -- thanks @exarkun! 
- Fixed an uncaught `TypeError` caused by a regression introduced by PyQt5 version 5.15.7 (Issue #496; PR #497)
- Unencrypted Recovery Keys will no longer default to using a ".encrypted" filename suffix (Issue #509; PR #511)
- Fixed a crash caused by attempting to disable autostart on Windows when the autostart shortcut/file has already been removed (Issue #512; PR #516)
- Fixed a race condition with a Supervisor restart test (PR #530) -- thanks @exarkun!
- Fixed an `OverflowError` caused by mixing/converting between Qt's C++ integers and python's `int`s when calculating "days remaining" (Issue #532; PRs #535, #540)

### Removed
- Removed support for the "magic-folder" Tahoe-LAFS feature removed in Tahoe-LAFS 1.15 (Issue #408; PR #411)
- Removed Nix expressions for packaging Gridsync with Nix (PR #413)
- Removed support for macOS 10.15/"Catalina" (Issue #510; PR #518)
- Removed support for Ubuntu 18.04/"Bionic Beaver" (Issue #538; PR #539)


## 0.5.0 - 2021-10-11
- No significant changes since 0.5.0rc2

## 0.5.0rc2 - 2021-10-08
### Added
- Added support for preserving/restoring the Tahoe-LAFS convergence secret via the Recovery Key (Issue #347; PR #356)
- Added/enabled support for fractional scaling of UI elements (Issue #357; PR #358)
- Added basic scripts to facilitate GPG and Authenticode signing (PR #380)
- Added a `0-test-grid` "[cheat code](https://github.com/gridsync/gridsync/blob/master/docs/cheat-codes.md)" for the Tahoe-LAFS "[Public Test Grid](https://tahoe-lafs.org/trac/tahoe-lafs/wiki/TestGrid)" (Issue #386; PR #387)

### Changed
- Updated Windows packaging to dynamically generate InnoSetup configuration file at build-time (Issue #348; PR #349)
- Updated Nix packaging -- thanks @exarkun! (PR #365)

### Fixed
- Fixed an issue with "Create Invite Code" button launching an incorrect dialog (Issue #345; PR #346)
- Fixed `make.bat` to properly propagate linter errors on Windows CI (Issue #350; PR #351)
- Improved error-handling when importing invalid Recovery Keys (Issue #359; PR #361)
- Fixed crash caused by entering non-ASCII voucher codes (Issue #360; PR #362)
- Disabled Preferences options for features disabled via `config.txt` (Issue #382; PR #383)
- Fixed/improved error-handling for failures pertaining to generating/adding ZKAPAuthorizer vouchers (Issue #381; PR #385)

### Deprecated
- This will be the final release of Gridsync that supports the `tahoe magic-folder` feature/subcommand. Magic-Folder was [removed from Tahoe-LAFS in version 1.15](https://github.com/tahoe-lafs/tahoe-lafs/blob/master/NEWS.rst#release-1150-2020-10-13) and split off into a [standalone project](https://github.com/LeastAuthority/magic-folder). Future releases of Gridsync will ship and use the standalone Magic-Folder application for Tahoe-LAFS-based file-synchronization.


## 0.5.0rc1 - 2021-03-25
### Added
- Added support for Python 3.8 (Issues #264, #269; PRs #270, #315)
- Added support for Python 3.9 (Issue #316; PR #336)
- Added support for macOS 11.0 ("Big Sur") (Issue #319; PR #320)
- Added support for building Gridsync on "Apple Silicon" (arm64) macs under the "Rosetta" translation environment (Issue #322; PR #323)
- Added support for building backward-compatible AppImages inside a CentOS 7-based container via `make in-container` (Issue #328; PR #329)
- Gridsync AppImages can now be built reproducibly across many common host environments (including Debian 10, Fedora 32, Ubuntu 20.04 LTS, and Ubuntu 20.10) using `make in-container` (Issue #330; PR #335)
- Gridsync binaries created with PyInstaller now build reproducibly on macOS and Windows (Issue #331, #332; PR #337)
- Added preliminary support for ZKAPAuthorizer-enabled storage grids (Issue #238; PR #338)
- Added a `0-hro-cloud` "[cheat code](https://github.com/gridsync/gridsync/blob/master/docs/cheat-codes.md)" for Least Authority's "[HRO Cloud](https://leastauthority.com/blog/the-hro-cloud-least-authority-launches-secure-cloud-storage-for-human-rights-organizations/)" (Issue #339; PR #340)

### Changed
- Binary distributions of Gridsync will now ship with Python version 3.9 (Issue #316; PR #336)
- The MainWindow's toolbar buttons/actions have been modified to facilitate the addition of ZKAPAuthorizer support (Issue #238; PR #338)

### Removed
- Python 3.6 is no longer supported (Issue #324; PR #325)
- macOS 10.13 ("High Sierra") is no longer supported (Issue #333; PR #334)
- The Gridsync project no longer depends on AppVeyor or Travis-CI for continuous integration and now uses GitHub Actions (Issues #326, #317, #304; PR #327, #318, #305)

### Fixed
- An issue preventing multiple Vagrant/VirtualBox environments from launching via `make vagrant-desktop-*` and/or `make vagrant-build-*` has been fixed (Issue #333; PR #334)


## 0.4.3 - 2020-07-24
### Added
- Basic support for fetching and displaying "newscap" messages; see `docs/proposed/newscaps.md` (Issue #184; PR #192, #211)
- Notification "badges" will now be displayed over the system tray icon to indicate unread newscap messages (Issue #226, PR #227)
- The application menu -- normally accessible by right-clicking the system tray icon -- is now also always accessible via a button in the status panel (Issue #201, PR #202)
- Clicking a desktop notification on Windows will now activate the main window (Issue #209; PR #210)
- macOS Mojave's "dark mode" is now supported (Issue #213, PR #217; Issue #267, PR #287)
- Added support for "cross-compiling" Gridsync binaries via Vagrant/VirtualBox; see `README.rst` (Issue #230, PR #231)
- Gridsync [AppImages](https://appimage.org/) are now available for GNU/Linux (Issue #245, PR #246, #248, #253)
- macOS builds have been [notarized](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution) (Issue #261, PR #278)
- An optional "default" grid-connection/configuration can now be specified via `config.txt`, facilitating custom deployments that omit "invite code"-based configuration (PR #292)
- It is now possible to disable some features at runtime by modifying `config.txt` (PR #293)

### Changed
- Binary distributions of Gridsync will now ship with Python version 3.7 (Issue #175; PR #187)
- The "remove" folder action and subsequent confirmation dialog have been re-framed/updated to "stop syncing" instead. In addition, removing/stopping a folder will now unlink it from the user's rootcap/Recovery Key by default (i.e., unless the user checks the accompanying checkbox to "keep a backup copy of this folder on $GridName") (Issue #183, PR #190)
- Various scripts, configurations, and operations relating to the Gridsync CI/testing/build process have been updated and improved, slightly reducing at least one developer's growing frustrations with Travis-CI and buildbot (PR #188)
- Twisted's `reactor.spawnProcess` will now be used for running `tahoe` subprocesses on Windows, instead of threaded `subprocess.Popen` calls (Issue #176, PR #195)
- GNU/Linux and Windows binary distributions will now use and ship with (Py)Qt version 5.15 (while macOS will use and ship 5.14, due to outstanding upstream bugs) (Issues #276, #267, #298; PRs #277, #287, #299)
- Due to ending upstream support and binary incompatibily with Qt 5.12, Debian 8 ("Jessie") and Ubuntu 14.04 ("Trusty Tahr") are no longer supported. Users running Debian 8 or Ubuntu 14.04 will need to upgrade their operating systems or build/install Gridsync from source (via `make`) (PR #196)
- High-DPI scaling (via Qt5's `AA_EnableHighDpiScaling` attribute) has been enabled on all platforms/environments (except for Qubes-OS and MATE -- see #204). In addition, font- and pixmap-scaling has been improved (Issue #193, #198, #232; PR #199, #203, #204, #233)
- The "Open Gridsync" menu action will now also un-minimize and re-focus the window in the event that it is already open (Issue #205; PR #206)
- Desktop notifications for connection/disconnection events are now disabled by default (Issue #218, PR #219)
- Binary distributions of Gridsync will now ship with Tahoe-LAFS version 1.14.0
- Python 3.5 support has been dropped; Gridsync now requires Python version 3.6 or higher (Issue #243, PR #244)
- Users are no longer required to scroll to the bottom of a debug log in order to export it (Issue #258, PR #259)
- [Versioneer](https://github.com/warner/python-versioneer) will now be used to manage version strings (PR #283; Issue #288, PR #289)
- On macOS, Gridsync will no longer run as an background-only/"agent" app; the application will again be visible in both the Dock and CMD+Tab window-list (Issue #284, PR #285)
- The grid-name will now be displayed in the status panel when "connected" instead of the number of connected/known storage nodes (Issue #296, PR #297)
- The number of connected/known storage nodes and total storage space remaining will now always be displayed in the status panel label's tooltip, instead of the (now-removed) "globe" icon/button (Issues #296, #300; PR #301)

### Removed
- Due to changes in minimum system requirements for numerous dependencies, macOS "Legacy" builds (targeting macOS 10.9 or higher) will no longer be provided (Issue #256, PR #266); Gridsync now requires a minimum macOS version of 10.13 or higher.

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
- The "drop zone" border (visually indicating, by means of a dotted line, the area capable of adding new folders via drag-and-drop) is now rendered programmatically according to the dimensions of the enclosing window, thus preventing the border from appearing disproportionately thick when the MainWindow is enlarged or maximized (Issue #75, PR #240)
- The poorly-supported-by-Qt macOS "fullscreen" mode has been disabled for the MainWindow (and replaced with a more traditional "maximize" functionality), preventing the situation in which the application window could become stuck in fullscreen mode (Issue #241, PR #242)
- Left-clicking the "Action" button corresponding to a specific folder will now correctly deselect and exclude any other folders from the subsequent user-selected action (Issue #254, PR #255)
- Folders joined while connecting to a new grid will now appear immediately in the MainWindow folders view after the setup process completes (Issue #256, PR #257)
- On Windows, Gridsync will attempt to remove any stale magic-folder sqlite databases on exit/restart, preventing an issue in which previously-joined folders could not be re-downloaded (Issue #294, PR #295)
- Folders will no longer be erroneously shown as being "Up to date" if their corresponding `tahoe` client is not connected to the storage grid or has not completed a remote scan (Issue #300, PR #301).
- The "Scanning" folder status/phase has been combined with the "Syncing" phase and will no longer be displayed separately (PR #301).

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
