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
    self,
    systems,
    nixpkgs,
    treefmt-nix,
    ...
  }: let
    perSystem = attrs:
      nixpkgs.lib.genAttrs (import systems) (system:
        attrs (import nixpkgs {
          inherit system;
          overlays = [self.overlays.default];
        }));

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
          (callPackage ({
            # nix build inputs
            buildPythonPackage,
            fetchPypi,
            # python deps
            hatchling,
            beautifulsoup4,
            lxml,
            curl-cffi,
            ...
          }: let
            pname = "letterboxdpy";
            version = "6.5.2";
          in
            buildPythonPackage {
              inherit pname version;

              pyproject = true;
              build-system = [hatchling];

              dependencies = [
                beautifulsoup4
                lxml
                curl-cffi
                (callPackage ({
                  # nix build inputs
                  buildPythonPackage,
                  fetchPypi,
                  # python deps
                  setuptools,
                  requests,
                  beautifulsoup4,
                  termcolor,
                  ...
                }: let
                  pname = "fastfingertips";
                  version = "0.1.4";
                in
                  buildPythonPackage {
                    inherit pname version;

                    pyproject = true;
                    build-system = [setuptools];

                    dependencies = [
                      requests
                      beautifulsoup4
                      termcolor
                    ];

                    src = fetchPypi {
                      inherit pname version;
                      hash = "sha256-weAIovKRCOHiNkrJm0uH/zeM5m4Q02RGzePzchGNS1o=";
                    };
                  }) {})
              ];

              src = fetchPypi {
                inherit pname version;
                hash = "sha256-zZRuMZvGN3z+4M5jcij66jBUXcwA+gbWJFYnbZQt/IA=";
              };
            }) {})
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
    overlays.default = final: _prev: {
      jellyfin-auto-collections = final.callPackage (
        {
          stdenv,
          makeWrapper,
          pkgs,
          ...
        }: let
          pname = "jellyfin-auto-collections";
          version = "0.0.0";

          interpreter =
            (pyEnv pkgs).interpreter;
        in
          stdenv.mkDerivation {
            inherit pname version;

            src = ./.;

            nativeBuildInputs = [
              makeWrapper
            ];

            installPhase = ''
              runHook preInstall

              mkdir -p $out/bin $out/share $out/share/Jellyfin-Auto-Collections
              cp -R ./{plugins,utils,*.py} $out/share/Jellyfin-Auto-Collections

              makeWrapper ${interpreter} $out/bin/${pname} \
                --add-flags "-u $out/share/Jellyfin-Auto-Collections/main.py" \
                --prefix PYTHONPATH : "$out/share/Jellyfin-Auto-Collections"

              runHook postInstall
            '';

            meta = {
              mainProgram = pname;
            };
          }
      ) {};
    };

    packages = perSystem (pkgs: rec {
      inherit (pkgs) jellyfin-auto-collections;
      default = jellyfin-auto-collections;
    });

    devShells = perSystem (pkgs: {
      default = pkgs.mkShell {
        packages = [(pyEnv pkgs)];
      };
    });

    formatter = perSystem (pkgs: let
      treefmtEval = treefmt-nix.lib.evalModule pkgs (import ./treefmt.nix pyEnv);
    in
      treefmtEval.config.build.wrapper);
  };
}
