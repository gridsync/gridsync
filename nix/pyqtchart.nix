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
  inherit (python3Packages) python pyqt5 buildPythonPackage;
  inherit (pyqt5) sip;
in buildPythonPackage rec {
  pname = "PyQtChart";
  version = "5.15.4";
  format = "other";

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
  ];
  buildInputs = [
    sip
    qtbase
    qtcharts
  ];
  propagatedBuildInputs = [
    pyqt5
  ];

  configurePhase = ''
    runHook preConfigure

    mkdir -p "$out/share/sip/PyQt5"

    # --no-dist-info disables mk_distinfo which wants to write dist-info to
    # the wrong place.  Fortunately the minimal dist-info required is simple so
    # we'll generate it ourselves below.
    ${python.executable} configure.py -w \
      --no-dist-info \
      --destdir="$out/${python.sitePackages}/PyQt5" \
      --apidir="$out/api/${python.libPrefix}" \
      --qtchart-sipdir="$out/share/sip/PyQt5" \
      --pyqt-sipdir="${pyqt5}/share/sip/PyQt5" \
      --stubsdir="$out/${python.sitePackages}/PyQt5"

    runHook postConfigure
  '';

  postInstall = ''
    # Let's make it a namespace package
    cat << EOF > $out/${python.sitePackages}/PyQt5/__init__.py
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
    EOF

    # Generate the minimal dist-info required to make the package
    # discoverable.
    mkdir -p $out/${python.sitePackages}/${pname}-${version}.dist-info
    cat << EOF > $out/${python.sitePackages}/${pname}-${version}.dist-info/METADATA
    Metadata-Version: 1.2
    Name: ${pname}
    Version: ${version}
    EOF
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
