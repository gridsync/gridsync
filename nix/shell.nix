{ pkgs ? import <nixpkgs> { overlays = [ (import ./overlays.nix) ]; } }:
let
  gridsync = pkgs.callPackage ./default.nix { };
  tahoe-lafs-env = pkgs.callPackage ./tahoe-lafs-env.nix { };
in
  pkgs.mkShell {
    buildInputs = [
      gridsync
      tahoe-lafs-env
    ];
  }
