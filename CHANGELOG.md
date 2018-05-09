# Changelog

## Unreleased
### Added
- Tor integration (EXPERIMENTAL)
    - Gridsync can now optionally tunnel outgoing connections through the Tor anonymity network; see [`docs/tor-integration.md`](https://github.com/gridsync/gridsync/blob/master/docs/tor-integration.md) (Issue #64)
- Application preferences are now also accessible from the initial welcome screen
- A "Restore from Recovery Key" link/option is now available directly from the initial welcome screen (Issue #60)

### Changed
- Due to upstream changes/deprecations with the Homebrew package manager, the minimum supported version of macOS for Gridsync binary distributions has been increased from 10.10 ("Yosemite") to 10.11 ("El Capitan"). Users of macOS 10.10 or lower are advised to either upgrade or build/install Gridsync from source.
- Icons for folders that have been shared will now be displayed with a "person" overlay instead of a green lock.
- Failure to decrypt a recovery key no longer requires re-importing the file to try again (Issue #60)

### Removed
- The "default" provider section of `config.txt` has been removed; organizations wishing to deploy a modified Gridsync client with pre-configured settings are encouraged to use a ["cheat code"](https://github.com/gridsync/gridsync/blob/master/docs/cheat-codes.md) instead

### Fixed
- `tahoe.select_executable()` will now use an empty nodedir when checking tahoe instances for multi-magic-folder support (preventing potential inaccuracies caused, e.g., by a pre-existing/misconfigured `$HOME/.tahoe` nodedir)
- Tahoe subclients created from older versions of Tahoe-LAFS that only support "legacy" magic-folders will now correctly inherit the parent client's `servers.yaml` settings upon creation.

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
