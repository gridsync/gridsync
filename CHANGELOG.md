# Changelog

## Unreleased
### Added
- "Start minimized" option to Preferences pane
- "Start automatically on login" option to Preferences pane (Issue #66)

### Changed
- The application will no longer start in a "minimized" state by default (Issue #69)
- Updated qt5reactor to wake up less often, reducing idle CPU consumption -- thanks @exarkun!

### Fixed
- "Last modified" time will no longer update until after the first remote scan has completed, thereby preventing misleading mtimes (e.g., "48 years ago") from being displayed briefly on start (Issue #63).
- Invites received through the "Add Folder" button will no longer appear to "hang" when receiving an invite that does not contain a magic-folder join-code (Issue #67)

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
