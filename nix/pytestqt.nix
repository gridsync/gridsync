{ python3Packages, fetchurl, setuptools_scm, pytest, pyqt5 }:
python3Packages.buildPythonPackage rec {
  version = "3.2.2";
  name = "pytest-qt-${version}";
  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/7c/9a/092c4a8ba026ed99b9741bf11d20fef24753e1cba49ed6d03c2077c35ae5/pytest-qt-3.2.2.tar.gz";
    sha256 = "f6ecf4b38088ae1092cbd5beeaf714516d1f81f8938626a2eac546206cdfe7fa";
  };
  buildInputs = [
    setuptools_scm
    pytest
    pyqt5
  ];
  doCheck = false;
}
