{
  inputs = {
    nixpkgs = {
      type = "git";
      url = "https://github.com/NixOS/nixpkgs";
      ref = "nixos-unstable";
      shallow = true;
    };

    treefmt-nix = {
      type = "github";
      owner = "numtide";
      repo = "treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    systems = {
      type = "github";
      owner = "nix-systems";
      repo = "default-linux";
    };
  };

  outputs = {
    systems,
    nixpkgs,
    treefmt-nix,
    ...
  }: let
    perSystem = attrs:
      nixpkgs.lib.genAttrs (import systems) (system:
        attrs (import nixpkgs {inherit system;}));

    pyEnv = pkgs:
      pkgs.python3Packages.python.withPackages (ps:
        with ps; [
          apscheduler
          beautifulsoup4
          certifi
          charset-normalizer
          contourpy
          cycler
          fonttools
          idna
          kiwisolver
          loguru
          pluginlib
          pyaml-env
          pytz
          pyyaml
          requests
          requests-cache
          setuptools
          six
          soupsieve
          tzlocal
          urllib3
          url-normalize
          numpy
          packaging
          pillow
          pyparsing
          python-dateutil
          attrs
          cattrs
          platformdirs
          pytest
        ]);
  in {
    formatter = perSystem (pkgs: let
      treefmtEval = treefmt-nix.lib.evalModule pkgs (import ./treefmt.nix pyEnv);
    in
      treefmtEval.config.build.wrapper);

    devShells = perSystem (pkgs: {
      default = pkgs.mkShell {
        packages = [(pyEnv pkgs)];
      };
    });
  };
}
