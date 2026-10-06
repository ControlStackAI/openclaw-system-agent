{
  description = "ControlStackAI resident OpenClaw system agent";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4";
    installer-source = {
      url = "github:ControlStackAI/agent-installer/6d02675cd8ce3323589ec9d7f44e99fcf50487a2";
      flake = false;
    };
    openclaw-source = {
      url = "github:openclaw/nix-openclaw/f62d33f760bcbdbc6a52ac589eae22bf99201f90";
      flake = false;
    };
  };
  outputs = { self, nixpkgs, openclaw-source, installer-source }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    upstream = import "${openclaw-source}/nix/packages" { inherit pkgs; };
    core = pkgs.callPackage ./adapters/nixos/package.nix { inherit installer-source; };
    live = nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [ self.nixosModules.liveImage ];
    };
  in {
    packages.${system} = {
      default = core;
      system-agent = core;
      openclaw = upstream.openclaw-gateway;
      live-iso = live.config.system.build.isoImage;
    };
    checks.${system} = {
      core-vm = import ./tests/core-vm.nix { inherit pkgs; module = self.nixosModules.default; };
      lifecycle-vm = import ./tests/nixos-vm.nix { inherit pkgs; module = self.nixosModules.default; };
    };
    nixosConfigurations.live = live;
    nixosModules.liveImage = { ... }: {
      imports = [ self.nixosModules.default ./adapters/nixos/live-image.nix ];
      services.controlstackAgent.installInputs = {
        nixpkgs = "${nixpkgs}";
        source = "${self}";
        core = "${core}";
        runtime = "${upstream.openclaw-gateway}";
        installer_revision = "6d02675cd8ce3323589ec9d7f44e99fcf50487a2";
      };
    };
    nixosModules.default = { ... }: {
      imports = [ ./adapters/nixos/module.nix ];
      services.controlstackAgent.package = pkgs.lib.mkDefault upstream.openclaw-gateway;
      services.controlstackAgent.corePackage = pkgs.lib.mkDefault core;
    };
  };
}
