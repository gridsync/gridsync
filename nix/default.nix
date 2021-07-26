{ pkgs ? import <nixpkgs> { } }:
let
  pspkgs = import (builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/PrivateStorageio/nixpkgs/archive/a5cbaadd9676e8c568061e92bbf5ad6a5d884ded.tar.gz";
    sha256 = "0q5zknsp0qb25ag9zr9bw1ap7pb3f76bxsw81ahxkzj4z5dw6k2f";
  }) { };

  # Get a number of GridSync dependencies which are either unpackaged in
  # Nixpkgs or for which the packaged versions are too old.
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
  tahoe-lafs-env = pspkgs.callPackage ./tahoe-lafs-env.nix { };
  gridsync = pkgs.python3Packages.callPackage ./gridsync.nix {
    inherit qt5reactor zxcvbn pytesttwisted pyqtchart pytestqt;
    inherit (pkgs.qt5) wrapQtAppsHook;
    inherit tahoe-lafs-env;
  };
in
  gridsync
