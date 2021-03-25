{ python3Packages, fetchFromGitHub }:
python3Packages.buildPythonPackage rec {
  version = "v4.4.28";
  name = "zxcvbn-${version}";
  src = fetchFromGitHub {
    owner = "dwolfhub";
    repo = "zxcvbn-python";
    rev = version;
    sha256 = "0xzlsqc9h0llfy19w4m39jgfcnvzqviv8jhgwn3r75kip97i5mvs";
  };
}
