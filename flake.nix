{
  description = "BuildSec dev shell: Python + uv + Node";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in {
      devShells = forAll (pkgs:
        let
          python = pkgs.python312; # project requires 3.11+
        in {
          default = pkgs.mkShell {
            packages = [ python pkgs.uv pkgs.nodejs_22 pkgs.git ];

            # Make uv use the Nix-provided interpreter instead of downloading one
            UV_PYTHON = "${python}/bin/python";
            UV_PYTHON_DOWNLOADS = "never";

            # Native libs that PyPI wheels (pydantic-core, jiter, ...) expect on NixOS
            shellHook = ''
              export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
                pkgs.stdenv.cc.cc.lib
                pkgs.zlib
              ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
              echo "BuildSec shell ready. First time? Run: ./scripts/init.sh"
            '';
          };
        });
    };
}
