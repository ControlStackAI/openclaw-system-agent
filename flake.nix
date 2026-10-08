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
    # Include the matching official Codex harness so first sign-in does not
    # need to install another agent runtime. The NixOS release stays 2026.9.5.
    nixosCodexPlugin = (pkgs.callPackage "${openclaw-source}/nix/lib/openclaw-runtime-plugin.nix" {
      linkOpenClawPeer = false;
    }) (import "${openclaw-source}/nix/generated/openclaw-runtime-plugins/codex.nix");
    nixosRuntime = upstream.openclaw-gateway.overrideAttrs (old: {
      installPhase = old.installPhase + "\n" + ''
        mkdir -p "$out/lib/openclaw/dist/extensions/codex" "$out/lib/openclaw/extensions/codex"
        cp -R ${nixosCodexPlugin}/. "$out/lib/openclaw/dist/extensions/codex/"
        cp ${nixosCodexPlugin}/openclaw.plugin.json "$out/lib/openclaw/extensions/codex/"
      '';
    });
    runtime = import ./runtimes/openclaw/package.nix { upstream = upstream.openclaw-gateway; inherit (pkgs) lib fetchNpmDeps; };
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
      openclaw = nixosRuntime;
      arch-openclaw = runtime;
      live-iso = live.config.system.build.isoImage;
      arch-runtime = pkgs.buildEnv {
        name = "controlstack-arch-runtime";
        paths = [ core runtime aiTools pkgs.mesa
          (pkgs.callPackage ./adapters/nixos/hypruse/package.nix { nativeTools = true; }) ];
      };
    };
    checks.${system} = {
      networking-vm = assert live.config.networking.wireless.enable;
        assert live.config.networking.wireless.dbusControlled;
        import ./tests/networking-vm.nix { inherit pkgs; };
      desktop-vm = import ./tests/desktop-vm.nix { inherit pkgs aiTools; module = self.nixosModules.default; };
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
        runtime = "${nixosRuntime}";
        ai_tools = "${aiTools}";
        zfs_compatibility = "${pkgs.zfs_2_4}/share/zfs/compatibility.d/openzfs-2.2";
        installer_revision = "6d02675cd8ce3323589ec9d7f44e99fcf50487a2";
      };
    };
    nixosModules.default = { ... }: {
      imports = [ ./adapters/nixos/module.nix ];
      services.controlstackAgent.package = pkgs.lib.mkDefault nixosRuntime;
      services.controlstackAgent.corePackage = pkgs.lib.mkDefault core;
    };
  };
}
