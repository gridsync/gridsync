let
  pkgs = import <nixpkgs> {};
in
  pkgs.fetchgit {
    url = "https://github.com/PrivateStorageio/ZKAPAuthorizer";
    # To update, see nix-prefetch-git.
    # For example:
    #
    # nix-prefetch-git \
    #    --leave-dotGit \
    #    --rev ...rev... \
    #    https://github.com/PrivateStorageio/ZKAPAuthorizer.git
    rev = "45a1ff7908eef5ef5224bd3a7ed12f5cf4fd6a4b";
    sha256 = "189hd0g3yyp6vqc4xm2cd3ypnj4nibnl6yvm4vjcifz6waw76a2l";

    # ZKAPAuthorizer uses Versioneer which requires a .git at build time.
    leaveDotGit = true;
  }
