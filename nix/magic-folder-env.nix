{ pkgs }:
let
  magic-folder-env = pkgs.python2.buildEnv.override {
    # twisted plugins causes collisions between any packages that supply
    # plugins.
    ignoreCollisions = true;
    extraLibs = [
      pkgs.python2Packages.magic-folder
    ];
  };
in
  magic-folder-env
