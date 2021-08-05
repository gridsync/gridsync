{ python2 }:
let
  magic-folder = python2.pkgs.callPackage ./magic-folder.nix { };
  magic-folder-env = python2.buildEnv.override {
    # twisted plugins causes collisions between any packages that supply
    # plugins.
    ignoreCollisions = true;
    extraLibs = [
      magic-folder
    ];
  };
in
  magic-folder-env
