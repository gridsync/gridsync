let
  pkgs = import <nixpkgs> {};
in
  pkgs.fetchFromGitHub {
    owner = "LeastAuthority";
    repo = "magic-folder";
    rev = "e86068ea8fc9cd7ad0c5d98892d992ccf3115e37";
    sha256 = "0q34q6pgiv3kzr2jw0551122j72n1dj65h0m194cg4dj0xc89bmp";
  }