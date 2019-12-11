{ pkgs ? import <nixpkgs> { overlays = [ (import ./overlays.nix) ]; } }:
let
  qt5reactor = pkgs.python3Packages.callPackage ./qt5reactor.nix { };
  zxcvbn = pkgs.python3Packages.callPackage ./zxcvbn.nix { };
  pytesttwisted = pkgs.python3Packages.callPackage ./pytesttwisted.nix { };
  pytestqt = pkgs.python3Packages.callPackage ./pytestqt.nix { };
  zkapauthorizer = pkgs.python2Packages.callPackage (import ./zkapauthorizer.nix) { };
  tahoe-lafs-env = pkgs.python2.buildEnv.override {
    ignoreCollisions = true;
    extraLibs = [
      # zkapauthorizer pulls in tahoe-lafs.  It might be better to reference
      # it explicitly here but I'm not sure how to reach it.
      zkapauthorizer
    ];
  };
in
  pkgs.python3Packages.callPackage ./gridsync.nix {
    inherit qt5reactor zxcvbn pytesttwisted pytestqt;
    inherit (pkgs.qt5) wrapQtAppsHook;
    inherit tahoe-lafs-env;
  }
