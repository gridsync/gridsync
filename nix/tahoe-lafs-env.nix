{ pkgs }:
let
  # For now GridSync requires this older tahoe-lafs because it still includes
  # magic-folder.
  tahoe-lafs = pkgs.python2Packages.tahoe-lafs-1_14;
  tahoe-lafs-env = pkgs.python2.buildEnv.override {
    # twisted plugins causes collisions between any packages that supply
    # plugins.
    ignoreCollisions = true;
    extraLibs = [
      tahoe-lafs
      (pkgs.python2Packages.zkapauthorizer.override { inherit tahoe-lafs; })
    ];
  };
in
  tahoe-lafs-env
