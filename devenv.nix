{
  pkgs,
  lib,
  ...
}: {
  cachix.enable = false;
  packages = with pkgs; [
    just
    uv
    python314
  ];
  env = {
    PYTHONNOUSERSITE = "1";
    UV_PYTHON = "3.14";
    UV_PYTHON_PREFERENCE = "only-system";
    UV_PYTHON_DOWNLOADS = "never";
    LD_LIBRARY_PATH = lib.makeLibraryPath [pkgs.stdenv.cc.cc.lib pkgs.zlib];
  };
  enterShell = ''
    unset PYTHONPATH PYTHONHOME _PYTHON_SYSCONFIGDATA_NAME
  '';
}
