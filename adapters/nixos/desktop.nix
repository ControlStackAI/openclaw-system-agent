{ desktop, aiTools ? null }:
assert builtins.elem desktop [ "none" "plasma" "gnome" "hyprland" ];
{ pkgs, ... }: {
  imports = [ ./development.nix ] ++ (if desktop == "hyprland" then [ ./hyprland ] else [ ]);
  environment.systemPackages = [ pkgs.mcp-nixos ] ++ (if aiTools == null then [] else [ aiTools ]);
  services.desktopManager.plasma6.enable = desktop == "plasma";
  services.displayManager.sddm.enable = builtins.elem desktop [ "plasma" "hyprland" ];
  services.desktopManager.gnome.enable = desktop == "gnome";
  services.displayManager.gdm.enable = desktop == "gnome";
}
