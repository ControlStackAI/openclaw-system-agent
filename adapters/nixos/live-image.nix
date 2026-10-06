{ lib, pkgs, modulesPath, config, ... }:
{
  imports = [ (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix") ];
  services.controlstackAgent = {
    enable = true;
    ephemeral = true;
    mutableProviderSetup = true;
    workspaceExecution = true;
    zfs.enable = true;
  };
  networking.hostName = "openclaw-live";
  networking.hostId = "c05a0002";
  networking.networkmanager.enable = true;
  networking.wireless.enable = lib.mkForce false;
  networking.useNetworkd = lib.mkForce false;
  services.resolved.enable = lib.mkForce false;
  services.timesyncd.enable = true;
  services.openssh.enable = lib.mkForce false;
  services.getty.autologinUser = lib.mkForce "root";
  boot.kernelParams = [ "console=ttyS0,115200" "console=tty0" ];
  environment.systemPackages = with pkgs; [ curl git parted gptfdisk dosfstools whois python3 ];
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
  image.fileName = lib.mkForce "controlstack-openclaw-nixos-x86_64.iso";
  isoImage.volumeID = "OPENCLAW_NIXOS";
  isoImage.squashfsCompression = "zstd -Xcompression-level 6";
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  system.stateVersion = "26.05";
}
