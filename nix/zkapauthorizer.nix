let
  pkgs = import <nixpkgs> {};
in
  pkgs.fetchFromGitHub {
    owner = "PrivateStorageio";
    repo = "ZKAPAuthorizer";
    rev = "b2aaa5f82c6d078bc38d0d8ab0e66d7be449caec";
    sha256 = "0zhnxba3ql8i0jcpbr8vid5rkvrsa7gvvw2465jq5vb10ivwnjkq";
  }