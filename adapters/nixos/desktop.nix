{ desktop, aiTools ? null }:
assert builtins.elem desktop [ "none" "plasma" "gnome" "hyprland" ];
{ pkgs, ... }: {
  imports = [ ./development.nix ] ++ (if desktop == "hyprland" then [ ./hyprland ] else [ ]);
  services.udev.packages = [ pkgs.libfido2 pkgs.yubikey-personalization ];
  environment.systemPackages = [ pkgs.mcp-nixos pkgs.libfido2
    (pkgs.makeDesktopItem {
      name = "controlstack-codex-sign-in";
      desktopName = "Coding Assistant Sign-in";
      comment = "Connect Codex using your browser or another device";
      exec = "system-agent-codex-login";
      terminal = true;
      icon = "dialog-password";
      categories = [ "Development" "Settings" ];
    }) ] ++ (if aiTools == null then [] else [ aiTools ]);
  services.desktopManager.plasma6.enable = desktop == "plasma";
  services.displayManager.sddm.enable = desktop == "plasma";
  services.desktopManager.gnome.enable = desktop == "gnome";
  services.displayManager.gdm.enable = desktop == "gnome";
}
