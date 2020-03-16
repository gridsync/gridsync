{ pkgs ? import <nixpkgs> { overlays = [ (import ./overlays.nix) ]; } }:
let
  qt5reactor = pkgs.python3Packages.callPackage ./qt5reactor.nix { };
  zxcvbn = pkgs.python3Packages.callPackage ./zxcvbn.nix { };
  pytesttwisted = pkgs.python3Packages.callPackage ./pytesttwisted.nix { };

  # PyQtChart is a Python library, too, but needs to be built a little
  # differently so it can find the various Qt libraries it binds.
  pyqtchart = pkgs.libsForQt5.callPackage ./pyqtchart.nix {
    # Make sure we build it for Python 3 since it's for GridSync which is a
    # Python 3 application.
    inherit (pkgs) python3Packages;
  };

  pytestqt = pkgs.python3Packages.callPackage ./pytestqt.nix { };
  tahoe-lafs-env = pkgs.callPackage ./tahoe-lafs-env.nix { };
  gridsync = pkgs.python3Packages.callPackage ./gridsync.nix {
    inherit qt5reactor zxcvbn pytesttwisted pyqtchart pytestqt;
    inherit (pkgs.qt5) wrapQtAppsHook;
    inherit tahoe-lafs-env;
  };
in
  gridsync
