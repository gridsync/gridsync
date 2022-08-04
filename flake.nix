{
  description = "GridSync, Tahoe-LAFS/magic-folder GUI";
  inputs.nixpkgs = {
    url = "github:NixOS/nixpkgs?ref=nixos-22.05";
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

      # The version of Python we'll use to set up the environment.
      pythonVersion = "python3.9";

      # Many Nix-related tools don't want the `.` in the Python derivation
      # identifier.  Generate a string in the right format for them.
      python = builtins.replaceStrings ["."] [""] pythonVersion;

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

      # Build an FHS user environment that contains Qt native library
      # dependencies and some Python tools.  This is suitable for running tox
      # in.  `runScript` is the command to run in the FHS env's chroot.
      makeDevShell = runScript: pkgs.buildFHSUserEnv {
        name = "dev-env";
        profile = (
          # Usually bytecode is just a nuisance - getting stale, taking more
          # time to read/write than it saves, or creating extra noise in the
          # checkout with generated files.
          ''
          export PYTHONDONTWRITEBYTECODE=1
          ''

          # If there are any Qt plugins installed on the host system then we
          # must not let information about them leak into the dev environment.
          # The PyQt/Qt libraries we use for GridSync are almost certainly not
          # compatible with whatever is on the system and if the two get too
          # close to each other, Qt tends to SIGABRT itself.
          #
          # Clear this plugin path environment variable so any host plugin
          # libraries aren't discovered.
          + ''
          unset QT_PLUGIN_PATH
          ''

          # tox has its own ideas about what the default Python should be,
          # without regard to what version of Python is actually available on
          # the system.  Convince it to agree with the environment we've set
          # up.
          + ''
          export TOX_BASEPYTHON=${pythonVersion}
          ''

          # Sometimes the information Qt dumps when this variable is set is
          # useful for debugging Qt-related problems (especially problems
          # finding or loading certain Qt plugins).  It's pretty noisy so it's
          # not on by default.
          + ''
          # export QT_DEBUG_PLUGINS=1
          ''
        );

        # Install some libraries in the environment (only versions for the
        # target architecture).
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
        inherit runScript;
      };

    in {
      devShells = {
        # The default is to run an interactive shell.
        default = (makeDevShell "bash").env;
      };

      apps.tox = {
        type = "app";
        # Run the env-entering script from the FHS user environment.
        # Arguments from the command line will be passed along.
        # pkgs/build-support/build-fhs-userenv/default.nix for gory details.
        program = "${makeDevShell "tox"}/bin/dev-env";
      };
    });
}
