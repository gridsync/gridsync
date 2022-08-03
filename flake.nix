{
  description = "GridSync, Tahoe-LAFS/magic-folder GUI";
  inputs.nixpkgs = {
    url = "github:NixOS/nixpkgs?rev=6cce09ce7f12e039318168ccfb0344426e17eec8";
  };
  inputs.flake-utils = {
    url = "github:numtide/flake-utils";
  };
  inputs.pypi-deps-db = {
    flake = false;
    url = "github:DavHau/pypi-deps-db";
  };
  inputs.mach-nix = {
    flake = true;
    url = "github:DavHau/mach-nix";
    inputs = {
      nixpkgs.follows = "nixpkgs";
      flake-utils.follows = "flake-utils";
      pypi-deps-db.follows = "pypi-deps-db";
    };
  };
  outputs = { self, nixpkgs, flake-utils, mach-nix, ... }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system: let

      python = "python39";

      pkgs = nixpkgs.legacyPackages.${system};

      tox-env = pkgs.${python}.withPackages (ps: [ ps.tox ] );

      tahoe-env = mach-nix.lib.${system}.mkPython {
        inherit python;
        requirements = ''
          tahoe-lafs
          zero-knowledge-access-pass-authorizer
        '';
      };

      magic-folder-env = mach-nix.lib.${system}.mkPython {
        inherit python;
        requirements = ''
          magic-folder
        '';
      };
    in rec {
      devShell = (pkgs.buildFHSUserEnv {
        name = "gridsync-env";
        profile = ''
          export PYTHONDONTWRITEBYTECODE=1
          unset QT_PLUGIN_PATH
        '';
        targetPkgs = pkgs: (with pkgs;
          [
            # GridSync depends on PyQt5.  The PyQt5 wheel bundles Qt5 itself
            # but not the dependencies of those libraries.  Supply them.
            libstdcxx5
            zlib
            glib
            libGL
            fontconfig
            freetype
            libxkbcommon
            xorg.libxcb
            xorg.libXext
            xorg.libX11
            xorg.xcbutil
            xorg.xcbutilwm
            xorg.xcbutilimage
            xorg.xcbutilkeysyms
            xorg.xcbutilrenderutil
            dbus.lib

            # Put tox into the environment for "easy" testing
            tox-env

            # GridSync also depends on `tahoe` and `magic-folder` CLI tools.
            tahoe-env
            magic-folder-env
          ]);
        runScript = "bash";
      }).env;
    });
}
