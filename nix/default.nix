{ pkgs ? import <nixpkgs> { overlays = [ (import ./overlays.nix) ]; } }:
let
  qt5reactor = pkgs.python3Packages.callPackage ./qt5reactor.nix { };
  zxcvbn = pkgs.python3Packages.callPackage ./zxcvbn.nix { };
  pytesttwisted = pkgs.python3Packages.callPackage ./pytesttwisted.nix { };
  pytestqt = pkgs.python3Packages.callPackage ./pytestqt.nix { };
  tahoe-lafs = pkgs.python2Packages.callPackage ./tahoe-lafs.nix { };
in
  pkgs.python3Packages.callPackage ./gridsync.nix {
    inherit qt5reactor zxcvbn pytesttwisted pytestqt tahoe-lafs;
    inherit (pkgs.qt5) wrapQtAppsHook;
  }
