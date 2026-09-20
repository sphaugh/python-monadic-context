{
  description = "monadic-context: a lightweight, type-safe dependency injection library";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        monadic-context = python.pkgs.buildPythonPackage {
          pname = "monadic-context";
          version = "0.2.2";
          pyproject = true;
          src = ./.;
          build-system = [ python.pkgs.poetry-core ];
          dependencies = pkgs.lib.optionals (python.pythonOlder "3.11") [ python.pkgs.typing-extensions ];
          nativeCheckInputs = with python.pkgs; [ pytestCheckHook pytest-cov hypothesis ];
          pythonImportsCheck = [ "monadic_context" ];
        };
      in {
        packages.default = monadic-context;

        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: with ps; [ pytest pytest-cov hypothesis isort ]))
            pkgs.ruff
          ];
          shellHook = "export PYTHONPATH=$PWD:$PYTHONPATH";
        };
      });
}
