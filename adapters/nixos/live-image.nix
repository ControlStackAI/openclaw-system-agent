{ lib, pkgs, modulesPath, config, ... }:
{
  imports = [ (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix") ./networking.nix ];
  services.controlstackAgent = {
    enable = true;
    ephemeral = true;
    # Query NixOS options/packages while planning installation; no desktop access.
    nixosMcp.enable = true;
    mutableProviderSetup = true;
    workspaceExecution = true;
    zfs.enable = true;
  };
  networking.hostName = "openclaw-live";
  networking.hostId = "c05a0002";
  services.timesyncd.enable = true;
  services.udev.packages = [ pkgs.libfido2 pkgs.yubikey-personalization ];
  services.openssh.enable = lib.mkForce false;
  services.getty.autologinUser = lib.mkForce "root";
  services.getty.helpLine = lib.mkForce "OpenClaw setup opens on the primary console. Remote login is off.";
  boot.kernelParams = [ "console=ttyS0,115200" "console=tty0" ];
  environment.systemPackages = with pkgs; [ curl git parted gptfdisk dosfstools whois python3 kbd ];
  environment.etc."controlstack-agent/keymaps".source = pkgs.runCommand "controlstack-live-keymaps" {
    nativeBuildInputs = [ pkgs.ckbcomp ];
  } ''
    mkdir -p "$out"
    for layout in us gb de fr es; do
      ckbcomp -model pc105 -layout "$layout" > "$out/$layout"
    done
  '';
  environment.etc."agent-installer/live-image".text = "nixos\n";
  environment.etc."agent-installer/image.json".text = builtins.toJSON {
    schema = 1; distro = "nixos"; runtime = "openclaw";
  };
  environment.interactiveShellInit = ''
    if [ "$(id -u)" = 0 ] && [ -t 0 ] && [ "$(tty)" = /dev/tty1 ] &&
       [ "''${CONTROLSTACK_SETUP_OPENED:-}" != 1 ]; then
      export CONTROLSTACK_SETUP_OPENED=1
      system-agent-setup
    fi
  '';
  image.baseName = lib.mkForce "controlstack-openclaw-nixos-x86_64";
  isoImage.volumeID = "OPENCLAW_NIXOS";
  isoImage.squashfsCompression = "zstd -Xcompression-level 6";
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  system.stateVersion = "26.05";
}
