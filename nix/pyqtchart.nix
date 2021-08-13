{ fetchurl
, pkgconfig
, python3Packages
, qmake
, qtbase
, qtcharts
, wrapQtAppsHook
, lib
}:
let
  inherit (python3Packages) python pyqt5 buildPythonPackage pyqt-builder;
  inherit (pyqt5) sip;
in buildPythonPackage rec {
  pname = "PyQtChart";
  version = "5.15.4";
  format = "pyproject";

  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/e6/af/dd493297922be2935ae2de34daea818940c4f747a98d09acaaa5e84cd1dd/${pname}-${version}.tar.gz";
    sha256 = "0x409mf3qfv4yq9fb091h85i57cqh20zmz97pkm0bqai51im0xz4";
  };
  nativeBuildInputs = [
    pkgconfig
    wrapQtAppsHook
    qmake
    sip
    qtbase
    qtcharts
    pyqt-builder
  ];
  buildInputs = [
    sip
    qtbase
    qtcharts
  ];
  propagatedBuildInputs = [
    pyqt5
  ];


  # Avoid running qmake, which is in nativeBuildInputs
  dontConfigure = true;

  postPatch = ''
    substituteInPlace pyproject.toml \
      --replace "[tool.sip.project]" "[tool.sip.project]''\nsip-include-dirs = [\"${pyqt5}/${python.sitePackages}/PyQt5/bindings\"]"
  '';

  installCheckPhase = let
    modules = [
      "PyQt5.QtChart"
    ];
    imports = lib.concatMapStrings (module: "import ${module};") modules;
  in ''
    echo "Checking whether modules can be imported..."
    PYTHONPATH=$PYTHONPATH:$out/${python.sitePackages} ${python.interpreter} -c "${imports}"
  '';

  doCheck = true;

  enableParallelBuilding = true;

  meta = with lib; {
    description = "Python bindings for Qt5Chart";
    homepage    = http://www.riverbankcomputing.co.uk;
    license     = licenses.gpl3;
    platforms   = platforms.mesaPlatforms;
  };
}
