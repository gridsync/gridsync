{ pkgs }:
let
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
  tahoe-lafs-env