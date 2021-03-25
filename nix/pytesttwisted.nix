# Copied and modified from https://github.com/garbas/nixpkgs-python/blob/master/pytest/requirements.nix
{ stdenv, fetchurl, python3Packages }:
python3Packages.buildPythonPackage {
  name = "pytest-twisted-1.10";
  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/17/42/7a08d581834054c909b9604ec97ff2d9e923c7eaa1ea7012248fb8e6045e/pytest-twisted-1.10.zip";
    sha256 = "b13a8c53c1763ce5a7497dfe60b67d766dafe2b50f1353be0dd098cf76be2eac";
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
