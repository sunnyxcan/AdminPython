{ pkgs }: {
  deps = [
    pkgs.python310Packages.pip
    pkgs.python310Packages.uvicorn
    pkgs.pkg-config # Untuk psycopg2-binary dan cryptography
    pkgs.libffi # Untuk cryptography
  ];
}