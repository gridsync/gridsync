let
  pkgs = import <nixpkgs> {};
in
  pkgs.fetchgit {
    url = "https://github.com/PrivateStorageio/ZKAPAuthorizer";
    rev = "45a1ff7908eef5ef5224bd3a7ed12f5cf4fd6a4b";
    sha256 = "0l7wp0bsg7ha8fkf7z4ilhfbmjnzzjd08znw8mbzja12r4fl7nmg";
    # ZKAPAuthorizer uses Versioneer which requires a .git at build time.
    leaveDotGit = true;
  }
