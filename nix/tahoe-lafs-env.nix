{ pkgs }:
let
  # Notice that ZKAPAuthorizer and the Tahoe-LAFS environment are built with
  # Python 2 because Tahoe-LAFS has not yet been ported to Python 3.  We have
  # to be careful not to mix these into the GridSync Python environment
  # because Python 2 and Python 3 stuff conflicts.
  zkapauthorizer = pkgs.python2Packages.callPackage (import ./zkapauthorizer.nix) { };
  tahoe-lafs-env = pkgs.python2.buildEnv.override {
    # twisted plugins causes collisions between any packages that supply
    # plugins.
    ignoreCollisions = true;
    extraLibs = [
      # zkapauthorizer pulls in tahoe-lafs.  It might be better to reference
      # it explicitly here but I'm not sure how to reach it.
      zkapauthorizer
    ];
  };
in
  tahoe-lafs-env
