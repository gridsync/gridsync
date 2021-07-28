# Copied and modified from https://github.com/garbas/nixpkgs-python/blob/master/pytest/requirements.nix
{ stdenv, fetchurl, python3Packages }:
python3Packages.buildPythonPackage {
  name = "pytest-twisted-1.13.3";
  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/2b/05/fb4addd4e1f86fad3bb52064139db15174f56b00df4ff8c2ad3c5edb01b6/pytest-twisted-1.13.3.tar.gz";
    sha256 = "08k3gqp9zn58ybhhs7f38pk756qmynmf86sczbrb0dw9q6h5c8x8";
  };
  doCheck = false;
  checkPhase = "";
  installCheckPhase = "";
  propagatedBuildInputs = [
    python3Packages.decorator
    python3Packages.greenlet
    python3Packages.pytest
  ];
  meta = with stdenv.lib; {
    homepage = "https://github.com/pytest-dev/pytest-twisted";
    license = "UNKNOWN";
    description = "A twisted plugin for py.test.";
  };
}
