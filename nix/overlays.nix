self: super: {
  python37 = super.python37.override {
    packageOverrides = python-self: python-super: {
      # sip = python-super.sip.overrideAttrs (oldAttrs: rec {
      #   version = "4.19.14";
      #   src = super.fetchurl {
      #     url = "https://www.riverbankcomputing.com/static/Downloads/sip/4.19.18/sip-4.19.18.tar.gz";
      #     sha256 = "07kyd56xgbb40ljb022rq82shgxprlbl0z27mpf1b6zd00w8dgf0";
      #   };
      # });
      # pyqt5 = python-super.pyqt5.overrideAttrs (oldAttrs: rec {
      #   version = "5.12.3";
      #   src = super.fetchurl {
      #     url = "https://www.riverbankcomputing.com/static/Downloads/PyQt5/${version}/PyQt5_gpl-${version}.tar.gz";
      #     sha256 = "041155bdzp57jy747p5d59740c55yy3241cy1x2lgcdsvqvzmc0d";
      #   };
      # });
    };
  };
}
