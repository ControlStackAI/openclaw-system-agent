{
  description = "ControlStackAI resident OpenClaw system agent";
  inputs = {
    llm-agents.url = "github:numtide/llm-agents.nix/59d0417c2017794f8872b5556f133c8b0b413734";
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
  outputs = { self, nixpkgs, openclaw-source, installer-source, llm-agents }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    ai = llm-agents.packages.${system};
    # GUI binaries must use the same libc as the system graphics drivers.
    desktopAi = (import nixpkgs {
      inherit system;
      config.allowUnfree = true;
      overlays = [ llm-agents.overlays.shared-nixpkgs ];
    }).llm-agents;
    aiTools = pkgs.buildEnv {
      name = "controlstack-ai-tools";
      paths = [ ai.codex ai.claude-code desktopAi.chatgpt
        (pkgs.symlinkJoin {
          name = "controlstack-claude-desktop";
          paths = [ desktopAi.claude-desktop ];
          nativeBuildInputs = [ pkgs.makeWrapper ];
          postBuild = ''
            wrapProgram "$out/bin/claude-desktop" --prefix LD_LIBRARY_PATH : "${pkgs.lib.makeLibraryPath [ pkgs.libglvnd ]}"
          '';
        })
        (pkgs.makeDesktopItem { name = "codex-cli"; desktopName = "Codex CLI"; genericName = "Terminal coding agent"; exec = "codex"; terminal = true; icon = "utilities-terminal"; categories = [ "Development" ]; })
        (pkgs.makeDesktopItem { name = "claude-cli"; desktopName = "Claude Code CLI"; genericName = "Terminal coding agent"; exec = "claude"; terminal = true; icon = "utilities-terminal"; categories = [ "Development" ]; })
        (pkgs.makeDesktopItem { name = "codex-desktop"; desktopName = "Codex Desktop"; genericName = "Codex in the official ChatGPT app"; exec = "chatgpt codex://"; icon = "chatgpt"; categories = [ "Development" ]; })
      ];
    };
    upstream = import "${openclaw-source}/nix/packages" { inherit pkgs; };
    core = pkgs.callPackage ./adapters/nixos/package.nix { inherit installer-source; };
    # Keep optional desktop closures on read-only media. Unpacking them into the
    # live tmpfs exhausted its space before the owner could approve installation.
    desktopClosures = map (desktop: (nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        (import ./adapters/nixos/desktop.nix { inherit desktop; aiTools = aiTools; })
        ({ pkgs, ... }: {
          boot.loader.grub.enable = false;
          boot.kernelPackages = pkgs.linuxPackages_latest;
          fileSystems."/" = { device = "/dev/disk/by-label/preload-only"; fsType = "ext4"; };
          networking.networkmanager.enable = true;
          hardware.enableRedistributableFirmware = true;
          environment.systemPackages = [ pkgs.xterm ];
          system.stateVersion = "26.05";
        })
      ];
    }).config.system.build.toplevel) [ "plasma" "gnome" "hyprland" ];
    live = nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [ self.nixosModules.liveImage ];
    };
  in {
    packages.${system} = {
      default = core;
      ai-tools = aiTools;
      system-agent = core;
      openclaw = upstream.openclaw-gateway;
      live-iso = live.config.system.build.isoImage;
    };
    checks.${system} = {
      desktop-vm = import ./tests/desktop-vm.nix { inherit pkgs aiTools; };
      core-vm = import ./tests/core-vm.nix { inherit pkgs; module = self.nixosModules.default; };
      lifecycle-vm = import ./tests/nixos-vm.nix { inherit pkgs; module = self.nixosModules.default; };
    };
    nixosConfigurations.live = live;
    nixosModules.liveImage = { ... }: {
      imports = [ self.nixosModules.default ./adapters/nixos/live-image.nix ];
      environment.systemPackages = [ ai.codex ai.claude-code pkgs.neovim ];
      environment.variables = { EDITOR = "nvim"; VISUAL = "nvim"; };
      isoImage.storeContents = desktopClosures;
      services.controlstackAgent.installInputs = {
        nixpkgs = "${nixpkgs}";
        source = "${self}";
        core = "${core}";
        runtime = "${upstream.openclaw-gateway}";
        ai_tools = "${aiTools}";
        zfs_compatibility = "${pkgs.zfs_2_4}/share/zfs/compatibility.d/openzfs-2.2";
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
